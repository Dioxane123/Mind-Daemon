#!/usr/bin/env python3
"""MCP Server for BCI Data Analysis, Monitoring and Alert System."""

import asyncio
import json
import csv
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from collections import Counter
import threading

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import Resource, Tool, TextContent
import mcp.server.stdio
import mcp.types as types

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from mind_daemon.utils.config import get_config

# Global variables
analysis_timer = None
monitoring_active = False
csv_file_path = None
analysis_history = []
alert_contacts = []

# Analysis parameters
NEGATIVE_STATES = ['cognitive_overload', 'drowsy', 'low_focus']
ALERT_THRESHOLD = 0.75  # 75% negative states
CONTINUOUS_ALERT_HOURS = 12  # 12 hours
ANALYSIS_INTERVAL = 900  # 15 minutes in seconds

server = Server("bci-analysis")


class BCIAnalysisEngine:
    """Core analysis engine for BCI data."""
    
    def __init__(self):
        self.config = get_config()
        
    def read_csv_data(self, csv_path: str, hours_back: float = 0.25) -> List[Dict]:
        """Read CSV data from the last specified hours."""
        if not os.path.exists(csv_path):
            return []
            
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        recent_data = []
        
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        # Handle different timestamp formats
                        timestamp_str = row['timestamp'].replace('Z', '+00:00')
                        if '+' not in timestamp_str and 'T' in timestamp_str:
                            timestamp_str += '+00:00'
                        
                        row_time = datetime.fromisoformat(timestamp_str)
                        if row_time.replace(tzinfo=None) >= cutoff_time:
                            recent_data.append(row)
                    except (ValueError, KeyError) as e:
                        continue
                        
        except Exception as e:
            print(f"❌ Error reading CSV: {e}")
            
        return recent_data
        
    def analyze_time_window(self, csv_path: str, hours_back: float = 0.25) -> Dict[str, Any]:
        """Analyze data from specified time window."""
        data = self.read_csv_data(csv_path, hours_back)
        
        if not data:
            return {
                "status": "no_data",
                "message": f"No data available for {hours_back*60:.0f}-minute analysis",
                "timestamp": datetime.now().isoformat(),
                "time_window_hours": hours_back
            }
        
        # Analyze cognitive states
        states = [row['cognitive_state'] for row in data if 'cognitive_state' in row]
        state_counts = Counter(states)
        total_records = len(states)
        
        if total_records == 0:
            return {
                "status": "no_valid_data",
                "message": "No valid cognitive state data found",
                "timestamp": datetime.now().isoformat()
            }
        
        # Calculate percentages
        state_percentages = {state: count/total_records for state, count in state_counts.items()}
        
        # Calculate negative state percentage
        negative_count = sum(state_counts.get(state, 0) for state in NEGATIVE_STATES)
        negative_percentage = negative_count / total_records
        
        # Analyze metrics trends
        metrics_analysis = self._analyze_metrics_trends(data)
        
        # Generate insights and recommendations
        insights = self._generate_insights(state_percentages, negative_percentage, metrics_analysis)
        recommendations = self._generate_recommendations(state_percentages, negative_percentage)
        
        analysis_result = {
            "timestamp": datetime.now().isoformat(),
            "time_window_hours": hours_back,
            "total_data_points": total_records,
            "state_distribution": state_percentages,
            "negative_state_percentage": negative_percentage,
            "dominant_state": max(state_counts, key=state_counts.get),
            "metrics_trends": metrics_analysis,
            "insights": insights,
            "alert_level": self._determine_alert_level(negative_percentage),
            "recommendations": recommendations,
            "system_status": self._analyze_system_usage(data)
        }
        
        return analysis_result
    
    def _analyze_metrics_trends(self, data: List[Dict]) -> Dict[str, Any]:
        """Analyze trends in BCI metrics."""
        metrics = ['attention_current', 'engagement_score', 'relaxation_score', 
                  'excitement_score', 'stress_score', 'focus_score']
        
        trends = {}
        for metric in metrics:
            values = []
            for row in data:
                try:
                    value = float(row.get(metric, 0))
                    if value > 0:  # Only include valid values
                        values.append(value)
                except (ValueError, TypeError):
                    continue
            
            if values:
                avg_value = sum(values) / len(values)
                trends[metric] = {
                    "average": avg_value,
                    "min": min(values),
                    "max": max(values),
                    "trend": self._calculate_trend(values),
                    "stability": self._calculate_stability(values)
                }
            else:
                trends[metric] = {
                    "average": 0, "min": 0, "max": 0, 
                    "trend": "no_data", "stability": "unknown"
                }
        
        return trends
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction for a metric."""
        if len(values) < 3:
            return "insufficient_data"
        
        first_third = sum(values[:len(values)//3]) / (len(values)//3)
        last_third = sum(values[-len(values)//3:]) / (len(values)//3)
        
        if last_third > first_third * 1.1:
            return "increasing"
        elif last_third < first_third * 0.9:
            return "decreasing"
        else:
            return "stable"
    
    def _calculate_stability(self, values: List[float]) -> str:
        """Calculate stability of a metric."""
        if len(values) < 2:
            return "unknown"
        
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        coefficient_of_variation = (variance ** 0.5) / mean_val if mean_val > 0 else float('inf')
        
        if coefficient_of_variation < 0.2:
            return "stable"
        elif coefficient_of_variation < 0.5:
            return "moderate"
        else:
            return "volatile"
    
    def _analyze_system_usage(self, data: List[Dict]) -> Dict[str, Any]:
        """Analyze halo and music system usage patterns."""
        halo_active_count = sum(1 for row in data if row.get('halo_active', '').lower() == 'true')
        music_playing_count = sum(1 for row in data if row.get('music_playing', '').lower() == 'true')
        
        total_records = len(data)
        
        return {
            "halo_usage_percentage": halo_active_count / total_records if total_records > 0 else 0,
            "music_usage_percentage": music_playing_count / total_records if total_records > 0 else 0,
            "system_engagement": (halo_active_count + music_playing_count) / (2 * total_records) if total_records > 0 else 0
        }
    
    def _generate_insights(self, state_percentages: Dict, negative_percentage: float, 
                          metrics_trends: Dict) -> List[str]:
        """Generate human-readable insights."""
        insights = []
        
        # State insights
        if negative_percentage > 0.7:
            insights.append("🚨 Critical: High levels of cognitive stress detected. Immediate intervention recommended.")
        elif negative_percentage > 0.5:
            insights.append("⚠️ Warning: Elevated cognitive load observed. Monitor closely and consider breaks.")
        elif negative_percentage > 0.3:
            insights.append("💡 Notice: Moderate cognitive load detected. Good to maintain awareness.")
        else:
            insights.append("✅ Positive: Cognitive state appears healthy and balanced.")
        
        # Attention insights
        if 'attention_current' in metrics_trends:
            attention = metrics_trends['attention_current']
            if attention['average'] > 0.7:
                insights.append(f"🎯 Excellent attention levels maintained (avg: {attention['average']:.2f})")
            elif attention['average'] < 0.4:
                insights.append(f"📉 Low attention detected (avg: {attention['average']:.2f}) - environment change recommended")
        
        # Stress insights  
        if 'stress_score' in metrics_trends:
            stress = metrics_trends['stress_score']
            if stress['average'] > 0.6:
                insights.append(f"😰 Elevated stress levels (avg: {stress['average']:.2f}) - relaxation techniques recommended")
            elif stress['trend'] == 'increasing':
                insights.append("📈 Stress levels trending upward - proactive measures advised")
        
        # Focus insights
        if 'focus_score' in metrics_trends:
            focus = metrics_trends['focus_score']
            if focus['trend'] == 'decreasing':
                insights.append("📉 Focus showing declining trend - consider task switching or breaks")
        
        return insights
    
    def _determine_alert_level(self, negative_percentage: float) -> str:
        """Determine alert level based on negative state percentage."""
        if negative_percentage >= 0.8:
            return "critical"
        elif negative_percentage >= 0.6:
            return "high"
        elif negative_percentage >= 0.4:
            return "medium"
        elif negative_percentage >= 0.2:
            return "low"
        else:
            return "normal"
    
    def _generate_recommendations(self, state_percentages: Dict, negative_percentage: float) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if negative_percentage > 0.8:
            recommendations.extend([
                "🛑 Take an immediate 15-20 minute break from all cognitive tasks",
                "🧘 Practice deep breathing or meditation exercises",
                "🚶 Consider a short walk or light physical activity",
                "💡 Evaluate and modify your work environment (lighting, noise, etc.)",
                "📅 Reassess your current workload and priorities"
            ])
        elif negative_percentage > 0.6:
            recommendations.extend([
                "⏸️ Take a 10-15 minute break within the next hour",
                "🎵 Consider calming background music or nature sounds",
                "💧 Ensure proper hydration and check posture",
                "🔄 Switch to a different type of task if possible",
                "⏰ Implement shorter work intervals with regular breaks"
            ])
        elif negative_percentage > 0.4:
            recommendations.extend([
                "👀 Monitor cognitive load and be prepared to take breaks",
                "🎯 Focus on one task at a time to reduce cognitive overhead",
                "☕ Consider a light snack or beverage break",
                "🌟 Acknowledge your current effort and progress"
            ])
        else:
            recommendations.extend([
                "✅ Current cognitive state is healthy - maintain current patterns",
                "📈 Continue with productive work sessions",
                "⚖️ Keep maintaining good work-rest balance",
                "🔋 Your mental energy levels appear sustainable"
            ])
        
        return recommendations
    
    def check_continuous_stress_alert(self, csv_path: str) -> Dict[str, Any]:
        """Check for continuous high-stress conditions over 12 hours."""
        data_12h = self.read_csv_data(csv_path, hours_back=12)
        
        if len(data_12h) < 10:
            return {
                "alert_needed": False, 
                "reason": "insufficient_data",
                "data_points": len(data_12h)
            }
        
        # Group data into hourly windows
        hourly_windows = {}
        for row in data_12h:
            try:
                timestamp_str = row['timestamp'].replace('Z', '+00:00')
                if '+' not in timestamp_str and 'T' in timestamp_str:
                    timestamp_str += '+00:00'
                
                row_time = datetime.fromisoformat(timestamp_str)
                hour_key = row_time.replace(minute=0, second=0, microsecond=0)
                
                if hour_key not in hourly_windows:
                    hourly_windows[hour_key] = []
                hourly_windows[hour_key].append(row['cognitive_state'])
            except (ValueError, KeyError):
                continue
        
        # Analyze each hour for negative state percentage
        high_stress_hours = 0
        total_hours = len(hourly_windows)
        hourly_analysis = []
        
        for hour_time, hour_states in hourly_windows.items():
            negative_count = sum(1 for state in hour_states if state in NEGATIVE_STATES)
            negative_percentage = negative_count / len(hour_states) if hour_states else 0
            
            is_high_stress = negative_percentage >= ALERT_THRESHOLD
            if is_high_stress:
                high_stress_hours += 1
            
            hourly_analysis.append({
                "hour": hour_time.strftime("%H:00"),
                "negative_percentage": negative_percentage,
                "is_high_stress": is_high_stress,
                "data_points": len(hour_states)
            })
        
        continuous_stress_percentage = high_stress_hours / total_hours if total_hours > 0 else 0
        
        alert_needed = (
            total_hours >= 8 and  # At least 8 hours of data
            continuous_stress_percentage >= ALERT_THRESHOLD  # 75%+ of hours were high stress
        )
        
        return {
            "alert_needed": alert_needed,
            "continuous_stress_percentage": continuous_stress_percentage,
            "high_stress_hours": high_stress_hours,
            "total_hours_analyzed": total_hours,
            "threshold": ALERT_THRESHOLD,
            "hourly_breakdown": hourly_analysis[-12:],  # Last 12 hours detail
            "severity": "critical" if continuous_stress_percentage > 0.9 else "high" if continuous_stress_percentage > ALERT_THRESHOLD else "moderate"
        }


class AlertManager:
    """Manage alerts and notifications."""
    
    def send_rest_reminder(self, analysis_data: Dict) -> Dict[str, Any]:
        """Generate rest reminder based on analysis."""
        alert_level = analysis_data.get('alert_level', 'normal')
        negative_pct = analysis_data.get('negative_state_percentage', 0)
        insights = analysis_data.get('insights', [])
        recommendations = analysis_data.get('recommendations', [])
        
        # Generate personalized message
        if alert_level == 'critical':
            message = "🚨 CRITICAL ALERT: Your cognitive stress levels are extremely high. Please stop all activities and take an immediate break for your wellbeing."
        elif alert_level == 'high':
            message = f"⚠️ HIGH ALERT: Significant cognitive stress detected ({negative_pct:.1%} negative states). A break is strongly recommended."
        elif alert_level == 'medium':
            message = f"💡 MODERATE ALERT: Elevated cognitive load observed ({negative_pct:.1%}). Consider taking a short break soon."
        else:
            message = f"ℹ️ NOTICE: Current cognitive state appears manageable ({negative_pct:.1%} negative states)."
        
        reminder = {
            "type": "rest_reminder",
            "severity": alert_level,
            "message": message,
            "negative_percentage": negative_pct,
            "insights": insights[:3],  # Top 3 insights
            "recommendations": recommendations[:5],  # Top 5 recommendations
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"📬 REST REMINDER GENERATED:")
        print(f"   Severity: {alert_level.upper()}")
        print(f"   Message: {message}")
        
        return reminder
    
    def generate_emergency_alert(self, stress_analysis: Dict) -> Dict[str, Any]:
        """Generate emergency alert for continuous stress."""
        alert = {
            "type": "emergency_alert",
            "severity": stress_analysis.get('severity', 'high'),
            "continuous_stress_percentage": stress_analysis['continuous_stress_percentage'],
            "hours_analyzed": stress_analysis['total_hours_analyzed'],
            "message": f"🚨 EMERGENCY: User has experienced {stress_analysis['continuous_stress_percentage']:.1%} high-stress cognitive states over {stress_analysis['total_hours_analyzed']} hours. Immediate attention and support may be needed.",
            "contacts_to_notify": len(alert_contacts),
            "timestamp": datetime.now().isoformat(),
            "hourly_breakdown": stress_analysis.get('hourly_breakdown', [])
        }
        
        print(f"🚨 EMERGENCY ALERT GENERATED:")
        print(f"   Stress Level: {stress_analysis['continuous_stress_percentage']:.1%} over {stress_analysis['total_hours_analyzed']}h")
        print(f"   Contacts to notify: {len(alert_contacts)}")
        
        # Placeholder for actual email sending
        for contact in alert_contacts:
            print(f"   📧 EMAIL PLACEHOLDER to {contact['email']}: Emergency stress alert")
        
        return alert


# Global instances
analysis_engine = BCIAnalysisEngine()
alert_manager = AlertManager()


def periodic_analysis_loop():
    """Main periodic analysis loop (15-minute intervals)."""
    global monitoring_active, csv_file_path, analysis_history
    
    print("🔄 Starting periodic analysis loop...")
    
    while monitoring_active:
        if csv_file_path and os.path.exists(csv_file_path):
            try:
                # Perform 15-minute analysis
                analysis = analysis_engine.analyze_time_window(csv_file_path, hours_back=0.25)
                analysis_history.append(analysis)
                
                # Keep only last 96 analysis records (24 hours worth)
                if len(analysis_history) > 96:
                    analysis_history = analysis_history[-96:]
                
                print(f"📊 15-min analysis: {analysis.get('alert_level', 'unknown')} level, {analysis.get('negative_state_percentage', 0):.1%} negative")
                
                # Generate rest reminder if needed
                if analysis.get('alert_level') in ['high', 'critical']:
                    alert_manager.send_rest_reminder(analysis)
                
                # Check for 12-hour continuous stress
                if len(analysis_history) >= 8:  # Only check after we have some history
                    stress_check = analysis_engine.check_continuous_stress_alert(csv_file_path)
                    if stress_check['alert_needed']:
                        emergency_alert = alert_manager.generate_emergency_alert(stress_check)
                        # Store emergency alert in history
                        analysis['emergency_alert'] = emergency_alert
                
            except Exception as e:
                print(f"❌ Analysis error: {e}")
                import traceback
                traceback.print_exc()
        
        # Wait for next analysis cycle (15 minutes)
        time.sleep(ANALYSIS_INTERVAL)


@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """List available analysis resources."""
    return [
        Resource(
            uri="analysis://status",
            name="Analysis System Status",
            description="Current status of the BCI analysis system",
            mimeType="application/json",
        ),
        Resource(
            uri="analysis://recent",
            name="Recent Analysis Results",
            description="Recent 15-minute analysis results",
            mimeType="application/json",
        ),
        Resource(
            uri="analysis://alerts",
            name="Alert History",
            description="History of alerts and emergency notifications",
            mimeType="application/json",
        ),
        Resource(
            uri="analysis://recommendations",
            name="Current Recommendations",
            description="Current recommendations based on latest analysis",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read analysis resource."""
    if uri == "analysis://status":
        status = {
            "monitoring_active": monitoring_active,
            "csv_file_path": csv_file_path,
            "analysis_count": len(analysis_history),
            "alert_contacts": len(alert_contacts),
            "last_analysis": analysis_history[-1]['timestamp'] if analysis_history else None,
            "analysis_interval_minutes": ANALYSIS_INTERVAL // 60
        }
        return json.dumps(status, indent=2)
        
    elif uri == "analysis://recent":
        recent = analysis_history[-10:] if analysis_history else []
        return json.dumps(recent, indent=2)
        
    elif uri == "analysis://alerts":
        alerts = [
            a for a in analysis_history 
            if a.get('alert_level') in ['high', 'critical'] or 'emergency_alert' in a
        ]
        return json.dumps(alerts[-20:], indent=2)  # Last 20 alerts
        
    elif uri == "analysis://recommendations":
        if analysis_history:
            latest = analysis_history[-1]
            recommendations = {
                "timestamp": latest['timestamp'],
                "alert_level": latest.get('alert_level', 'unknown'),
                "recommendations": latest.get('recommendations', []),
                "insights": latest.get('insights', []),
                "negative_state_percentage": latest.get('negative_state_percentage', 0)
            }
            return json.dumps(recommendations, indent=2)
        else:
            return json.dumps({"message": "No analysis data available"}, indent=2)
        
    else:
        raise ValueError(f"Unknown resource: {uri}")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available analysis tools."""
    return [
        Tool(
            name="start_monitoring",
            description="Start periodic BCI data analysis and monitoring",
            inputSchema={
                "type": "object",
                "properties": {
                    "csv_file_path": {
                        "type": "string",
                        "description": "Path to the CSV file containing BCI data"
                    }
                },
                "required": ["csv_file_path"],
                "additionalProperties": False
            },
        ),
        Tool(
            name="stop_monitoring", 
            description="Stop periodic analysis and monitoring",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            },
        ),
        Tool(
            name="analyze_current_state",
            description="Perform immediate analysis of recent data (15 minutes)",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            },
        ),
        Tool(
            name="analyze_time_window",
            description="Analyze data from a specific time window",
            inputSchema={
                "type": "object",
                "properties": {
                    "hours_back": {
                        "type": "number",
                        "minimum": 0.1,
                        "maximum": 24.0,
                        "description": "Hours of data to analyze (e.g., 0.25 for 15 minutes)"
                    }
                },
                "required": ["hours_back"],
                "additionalProperties": False
            },
        ),
        Tool(
            name="check_stress_alert",
            description="Check for 12-hour continuous stress conditions",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            },
        ),
        Tool(
            name="add_emergency_contact",
            description="Add emergency contact for stress alerts",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "format": "email",
                        "description": "Email address for emergency contact"
                    },
                    "name": {
                        "type": "string",
                        "description": "Name of the contact person"
                    },
                    "relationship": {
                        "type": "string",
                        "description": "Relationship to user (e.g., family, colleague, doctor)"
                    }
                },
                "required": ["email", "name"],
                "additionalProperties": False
            },
        ),
        Tool(
            name="get_wellness_report",
            description="Generate comprehensive wellness report",
            inputSchema={
                "type": "object",
                "properties": {
                    "hours_back": {
                        "type": "number",
                        "minimum": 1.0,
                        "maximum": 168.0,  # 1 week
                        "description": "Hours of data to include in report"
                    }
                },
                "additionalProperties": False
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls."""
    global monitoring_active, csv_file_path, analysis_timer, alert_contacts
    
    if name == "start_monitoring":
        csv_path = arguments.get("csv_file_path")
        
        if not os.path.exists(csv_path):
            return [types.TextContent(
                type="text",
                text=f"❌ CSV file not found: {csv_path}"
            )]
        
        csv_file_path = csv_path
        
        if not monitoring_active:
            monitoring_active = True
            
            # Start periodic analysis in background thread
            analysis_timer = threading.Thread(target=periodic_analysis_loop, daemon=True)
            analysis_timer.start()
            
            return [types.TextContent(
                type="text",
                text=f"✅ BCI analysis monitoring started\n📊 Analyzing data from: {csv_path}\n⏰ 15-minute analysis intervals active"
            )]
        else:
            return [types.TextContent(
                type="text",
                text="⚠️ Monitoring is already active"
            )]
            
    elif name == "stop_monitoring":
        monitoring_active = False
        return [types.TextContent(
            type="text",
            text="⏹️ BCI analysis monitoring stopped"
        )]
        
    elif name == "analyze_current_state":
        if not csv_file_path:
            return [types.TextContent(
                type="text",
                text="❌ No CSV file configured. Start monitoring first."
            )]
        
        analysis = analysis_engine.analyze_time_window(csv_file_path, hours_back=0.25)
        analysis_history.append(analysis)
        
        # Generate summary
        summary = {
            "alert_level": analysis.get('alert_level', 'unknown'),
            "negative_percentage": analysis.get('negative_state_percentage', 0),
            "dominant_state": analysis.get('dominant_state', 'unknown'),
            "key_insights": analysis.get('insights', [])[:3],
            "top_recommendations": analysis.get('recommendations', [])[:3]
        }
        
        return [types.TextContent(
            type="text",
            text=f"📊 Current State Analysis:\n{json.dumps(summary, indent=2)}"
        )]
        
    elif name == "analyze_time_window":
        if not csv_file_path:
            return [types.TextContent(
                type="text",
                text="❌ No CSV file configured. Start monitoring first."
            )]
        
        hours_back = arguments.get("hours_back", 0.25)
        analysis = analysis_engine.analyze_time_window(csv_file_path, hours_back=hours_back)
        
        return [types.TextContent(
            type="text",
            text=json.dumps(analysis, indent=2)
        )]
        
    elif name == "check_stress_alert":
        if not csv_file_path:
            return [types.TextContent(
                type="text",
                text="❌ No CSV file configured. Start monitoring first."
            )]
        
        stress_check = analysis_engine.check_continuous_stress_alert(csv_file_path)
        
        if stress_check['alert_needed']:
            emergency_alert = alert_manager.generate_emergency_alert(stress_check)
            result = {**stress_check, "emergency_alert": emergency_alert}
        else:
            result = stress_check
        
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
        
    elif name == "add_emergency_contact":
        email = arguments.get("email")
        name = arguments.get("name", "Unknown")
        relationship = arguments.get("relationship", "Contact")
        
        contact_info = {
            "email": email,
            "name": name, 
            "relationship": relationship,
            "added": datetime.now().isoformat()
        }
        alert_contacts.append(contact_info)
        
        return [types.TextContent(
            type="text",
            text=f"✅ Emergency contact added: {name} ({relationship}) - {email}"
        )]
        
    elif name == "get_wellness_report":
        if not csv_file_path:
            return [types.TextContent(
                type="text",
                text="❌ No CSV file configured. Start monitoring first."
            )]
        
        hours_back = arguments.get("hours_back", 24.0)
        
        # Generate comprehensive analysis
        analysis = analysis_engine.analyze_time_window(csv_file_path, hours_back=hours_back)
        stress_check = analysis_engine.check_continuous_stress_alert(csv_file_path)
        
        wellness_report = {
            "report_period_hours": hours_back,
            "generated_at": datetime.now().isoformat(),
            "overall_analysis": analysis,
            "stress_assessment": stress_check,
            "wellness_score": self._calculate_wellness_score(analysis),
            "summary": self._generate_wellness_summary(analysis, stress_check)
        }
        
        return [types.TextContent(
            type="text",
            text=json.dumps(wellness_report, indent=2)
        )]
        
    else:
        raise ValueError(f"Unknown tool: {name}")


def _calculate_wellness_score(analysis: Dict) -> float:
    """Calculate overall wellness score (0-100)."""
    if analysis.get('status') in ['no_data', 'no_valid_data']:
        return 0.0
    
    negative_pct = analysis.get('negative_state_percentage', 0)
    
    # Base score from state distribution
    base_score = (1 - negative_pct) * 100
    
    # Adjust based on metrics
    metrics = analysis.get('metrics_trends', {})
    adjustments = 0
    
    if 'attention_current' in metrics:
        attention_avg = metrics['attention_current'].get('average', 0)
        if attention_avg > 0.7:
            adjustments += 5
        elif attention_avg < 0.3:
            adjustments -= 10
    
    if 'stress_score' in metrics:
        stress_avg = metrics['stress_score'].get('average', 0)
        if stress_avg > 0.7:
            adjustments -= 15
        elif stress_avg < 0.3:
            adjustments += 5
    
    final_score = max(0, min(100, base_score + adjustments))
    return round(final_score, 1)


def _generate_wellness_summary(analysis: Dict, stress_check: Dict) -> List[str]:
    """Generate human-readable wellness summary."""
    summary = []
    
    if analysis.get('status') in ['no_data', 'no_valid_data']:
        summary.append("❌ Insufficient data for wellness assessment")
        return summary
    
    negative_pct = analysis.get('negative_state_percentage', 0)
    alert_level = analysis.get('alert_level', 'unknown')
    
    # Overall assessment
    if negative_pct < 0.2:
        summary.append("🌟 Excellent cognitive wellness - maintaining healthy mental state")
    elif negative_pct < 0.4:
        summary.append("✅ Good cognitive wellness - minor areas for attention")
    elif negative_pct < 0.6:
        summary.append("⚠️ Moderate concern - cognitive load management needed")
    else:
        summary.append("🚨 High concern - immediate wellness intervention recommended")
    
    # Stress assessment
    if stress_check.get('alert_needed'):
        summary.append(f"🔥 Critical: {stress_check['continuous_stress_percentage']:.1%} of time in high-stress state over {stress_check['total_hours_analyzed']} hours")
    
    # Add key insights
    insights = analysis.get('insights', [])
    if insights:
        summary.extend(insights[:2])  # Top 2 insights
    
    return summary


async def main():
    """Main server function."""
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="bci-analysis",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
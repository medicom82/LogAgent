"""Google Gemini AI Integration for LogAgent"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, List
import google.generativeai as genai
from database import execute_query
import json

logger = logging.getLogger(__name__)


class GeminiAnalyzer:
    """Analyzer using Google Gemini AI for log analysis and query generation"""
    
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model_name = os.getenv('GEMINI_MODEL', 'gemini-pro')
        self.temperature = float(os.getenv('GEMINI_TEMPERATURE', '0.3'))
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        
        logger.info(f"Initialized Gemini AI with model: {self.model_name}")
    
    def analyze_anomaly(self, anomaly_data: Dict) -> Dict:
        """Analyze detected anomaly using Gemini AI
        
        Args:
            anomaly_data: Dictionary containing anomaly details
            
        Returns:
            Analysis results with threat assessment and recommendations
        """
        try:
            prompt = self._build_anomaly_prompt(anomaly_data)
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=2048
                )
            )
            
            analysis = {
                'analysis_text': response.text,
                'timestamp': datetime.now().isoformat(),
                'model': self.model_name,
                'input_tokens': response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                'output_tokens': response.usage_metadata.candidates_token_count if response.usage_metadata else 0
            }
            
            # Save interaction to database
            self._save_interaction(
                prompt_type='anomaly_analysis',
                input_text=prompt[:5000],
                output_text=response.text[:5000],
                tokens_input=analysis['input_tokens'],
                tokens_output=analysis['output_tokens'],
                related_anomaly_id=anomaly_data.get('anomaly_id')
            )
            
            logger.info(f"Completed anomaly analysis for anomaly_id: {anomaly_data.get('anomaly_id')}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing anomaly with Gemini: {e}")
            raise
    
    def generate_query(self, anomaly_data: Dict) -> str:
        """Generate SQL query to investigate anomaly
        
        Args:
            anomaly_data: Dictionary containing anomaly details
            
        Returns:
            Generated SQL query string
        """
        try:
            prompt = self._build_query_prompt(anomaly_data)
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,  # Lower temperature for more deterministic output
                    max_output_tokens=1024
                )
            )
            
            query = response.text.strip()
            
            # Clean up query if wrapped in markdown code blocks
            if query.startswith('```sql'):
                query = query[6:]
            if query.startswith('```'):
                query = query[3:]
            if query.endswith('```'):
                query = query[:-3]
            query = query.strip()
            
            # Save interaction
            self._save_interaction(
                prompt_type='query_generation',
                input_text=prompt[:5000],
                output_text=query[:5000],
                tokens_input=response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                tokens_output=response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
                related_anomaly_id=anomaly_data.get('anomaly_id')
            )
            
            logger.info(f"Generated query for anomaly_id: {anomaly_data.get('anomaly_id')}")
            return query
            
        except Exception as e:
            logger.error(f"Error generating query with Gemini: {e}")
            raise
    
    def summarize_logs(self, logs: List[Dict]) -> str:
        """Summarize batch of logs
        
        Args:
            logs: List of log entries
            
        Returns:
            Natural language summary
        """
        try:
            log_text = "\n".join([f"- {log.get('log_type')}: {log.get('raw_log_line')}" for log in logs[:50]])
            
            prompt = f"""
Please provide a concise summary of the following logs, highlighting any concerning patterns:

{log_text}

Summary (max 3 sentences):
"""
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=500
                )
            )
            
            self._save_interaction(
                prompt_type='log_summary',
                input_text=log_text[:5000],
                output_text=response.text[:5000],
                tokens_input=response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                tokens_output=response.usage_metadata.candidates_token_count if response.usage_metadata else 0
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error summarizing logs: {e}")
            raise
    
    def threat_analysis(self, log_sample: str, context: str = "") -> Dict:
        """Perform threat intelligence analysis
        
        Args:
            log_sample: Sample of logs to analyze
            context: Additional context about the environment
            
        Returns:
            Threat analysis with indicators and recommendations
        """
        try:
            prompt = f"""
Perform cybersecurity threat analysis on the following log sample:

{log_sample}

Context: {context}

Please identify:
1. Potential threat indicators
2. Attack patterns
3. Confidence score (0-100)
4. Recommended immediate actions
5. Long-term security recommendations

Provide response in JSON format with keys: threat_indicators, attack_patterns, confidence_score, immediate_actions, long_term_recommendations
"""
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=2048
                )
            )
            
            # Try to parse JSON response
            try:
                result = json.loads(response.text)
            except json.JSONDecodeError:
                result = {'analysis': response.text}
            
            self._save_interaction(
                prompt_type='threat_analysis',
                input_text=log_sample[:5000],
                output_text=response.text[:5000],
                tokens_input=response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                tokens_output=response.usage_metadata.candidates_token_count if response.usage_metadata else 0
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error performing threat analysis: {e}")
            raise
    
    def get_recommendations(self, anomaly_summary: str, severity: str) -> List[str]:
        """Get recommendations based on anomalies
        
        Args:
            anomaly_summary: Summary of detected anomalies
            severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL)
            
        Returns:
            List of recommendations
        """
        try:
            prompt = f"""
Based on these detected security anomalies (Severity: {severity}):

{anomaly_summary}

Provide specific, actionable security recommendations in the following order:
1. Immediate actions (0-24 hours)
2. Short-term improvements (1-7 days)
3. Long-term hardening (1+ months)

Format each recommendation as a bullet point.
"""
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1024
                )
            )
            
            recommendations = [line.strip() for line in response.text.split('\n') if line.strip().startswith('•') or line.strip().startswith('-')]
            
            self._save_interaction(
                prompt_type='recommendation',
                input_text=anomaly_summary[:5000],
                output_text=response.text[:5000],
                tokens_input=response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                tokens_output=response.usage_metadata.candidates_token_count if response.usage_metadata else 0
            )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    def _build_anomaly_prompt(self, anomaly_data: Dict) -> str:
        """Build prompt for anomaly analysis"""
        return f"""
Analyze the following security log anomaly and provide insights:

Log Type: {anomaly_data.get('log_type', 'unknown')}
Timestamp: {anomaly_data.get('timestamp', 'unknown')}
Severity: {anomaly_data.get('severity', 'UNKNOWN')}
Anomaly Type: {anomaly_data.get('anomaly_type', 'unknown')}
Description: {anomaly_data.get('description', 'N/A')}

Log Details:
{anomaly_data.get('log_details', 'N/A')}

Please provide:
1. Potential threat assessment
2. Root cause analysis
3. Recommended immediate actions
4. Risk level (1-10)
5. Suggested investigation queries
"""
    
    def _build_query_prompt(self, anomaly_data: Dict) -> str:
        """Build prompt for query generation"""
        return f"""
Generate an SQL query to investigate the following detected anomaly:

Anomaly Type: {anomaly_data.get('anomaly_type', 'unknown')}
Server: {anomaly_data.get('server_id', 'unknown')}
Database: {anomaly_data.get('database', 'logagent')}
Time Window: {anomaly_data.get('time_window', 'last 24 hours')}
Anomaly Details: {anomaly_data.get('description', 'N/A')}

Generate ONLY a valid SQL query (no explanation) that will help investigate this anomaly.
The query should:
- Target the MySQL database with the schema including: logs, anomalies, baseline_metrics tables
- Return relevant log entries and metrics related to this anomaly
- Include appropriate WHERE conditions and ORDER BY
- Be executable on a MySQL 8.0+ database
"""
    
    def _save_interaction(self, prompt_type: str, input_text: str, output_text: str, 
                         tokens_input: int = 0, tokens_output: int = 0, 
                         related_anomaly_id: Optional[int] = None,
                         related_log_id: Optional[int] = None):
        """Save Gemini interaction to database"""
        try:
            query = """
INSERT INTO gemini_interactions 
(timestamp, prompt_type, input_text, output_text, model, tokens_input, tokens_output, 
 response_time_ms, is_success, related_anomaly_id, related_log_id)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
            execute_query(query, (
                datetime.now(),
                prompt_type,
                input_text,
                output_text,
                self.model_name,
                tokens_input,
                tokens_output,
                0,  # response_time_ms - can be calculated if needed
                True,
                related_anomaly_id,
                related_log_id
            ))
        except Exception as e:
            logger.error(f"Error saving Gemini interaction: {e}")


# Factory function
def get_gemini_analyzer() -> GeminiAnalyzer:
    """Get or create Gemini analyzer instance"""
    return GeminiAnalyzer()

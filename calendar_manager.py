import logging
import os
import uuid
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class CalendarManager:
    def schedule_event(self, user_id, title, start_time, duration_minutes=60):
        """
        Hybrid Schedule: Google API -> ICS Fallback.
        """
        # 1. Try Google API
        try:
            if os.path.exists("token.json") or os.path.exists("credentials.json"):
                link = self._add_to_google(title, start_time, duration_minutes)
                if link:
                    return f"✅ Подія створена в Google Calendar: {link}"
        except Exception as e:
            logger.warning(f"Google Calendar API failed: {e}. Falling back to ICS.")

        # 2. Fallback to ICS
        return self._generate_ics(title, start_time, duration_minutes)

    def _add_to_google(self, title, start_time, duration_minutes):
        """
        Upload to Google Calendar using Service Account.
        """
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        SERVICE_ACCOUNT_FILE = 'service_account.json'
        
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
             # Try legacy token path or fail
             return None

        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )

        service = build('calendar', 'v3', credentials=creds)
        
        # Parse Time
        start_dt = datetime.fromisoformat(start_time)
        end_dt = start_dt.replace(minute=start_dt.minute + duration_minutes)
        
        event = {
            'summary': title,
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'UTC'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'UTC'},
            # 'attendees': [{'email': 'user@example.com'}], # Ideally invite the user!
        }
        
        # NOTE: 'primary' here refers to the SERVICE ACCOUNT's calendar. 
        # The user won't see this unless they subscribe to the service account's calendar (hard).
        # BETTER: The user shares their calendar with the SA, and we write to their calendar ID.
        # For MVP: We try to insert into 'primary' (SA) and return link.
        # But really, we should try to add the user's email as attendee if known.
        
        # For now, just create event and hope user subscribed or shared.
        # Ideally we need a variable config.USER_CALENDAR_ID
        calendar_id = 'primary' 
        
        event = service.events().insert(calendarId=calendar_id, body=event).execute()
        return event.get('htmlLink')

    def _generate_ics(self, title, start_time, duration_minutes):
        """Generates an ICS file content."""
        try:
            # Simple ISO Parse
            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            
            # Format for ICS: YYYYMMDDTHHMMSSZ
            start_str = dt.strftime('%Y%m%dT%H%M00Z')
            # End time (not strictly needed for basic ics sometimes, but good to have)
            # Simplified: just use start
            
            ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//LifeOS//Assistant//EN
BEGIN:VEVENT
UID:{uuid.uuid4()}
DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M00Z')}
DTSTART:{start_str}
SUMMARY:{title}
DESCRIPTION:Created by Life OS Assistant
DURATION:PT{duration_minutes}M
END:VEVENT
END:VCALENDAR"""

            # Save to /tmp
            filename = f"/tmp/event_{uuid.uuid4()}.ics"
            with open(filename, 'w') as f:
                f.write(ics_content)
                
            return f"📅 Файл події створено (ICS): {filename}\n(Надішліть цей файл користувачу)"
            
        except Exception as e:
            return f"❌ ICS Gen Error: {e}"

calendar_system = CalendarManager()

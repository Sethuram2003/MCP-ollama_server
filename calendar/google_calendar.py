import os
import sys
import io
from typing import Optional, List
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from mcp.server.fastmcp import FastMCP

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    

mcp = FastMCP("google_calendar")

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Configuration paths
CREDENTIALS_FILE = "/home/gautham/Documents/random_data_engineering_projects/custom_MCP_client/calendar/credentials.json"
TOKEN_FILE = "/home/gautham/Documents/random_data_engineering_projects/custom_MCP_client/calendar/token.json"

from datetime import datetime, timedelta
import re

def convert_to_iso_datetime(datetime_str: str) -> str:
    """
    Convert a datetime string to ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
    Handles common formats without using dateutil package.
    
    Args:
        datetime_str: String containing date/time (e.g., "2024-12-25 14:00", "2pm")
    
    Returns:
        str: Datetime in ISO 8601 format
    
    Raises:
        ValueError: If the input string cannot be parsed as a valid datetime
    """
    try:
        # Try standard ISO format first
        try:
            dt = datetime.fromisoformat(datetime_str)
            
            return dt.isoformat(timespec='seconds')
        except ValueError:
            pass

        # Current time for relative calculations
        now = datetime.now()
        
        # Handle relative dates (today, tomorrow)
        if datetime_str.lower().startswith('today'):
            time_part = datetime_str[5:].strip()
            dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif datetime_str.lower().startswith('tomorrow'):
            time_part = datetime_str[8:].strip()
            dt = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            time_part = datetime_str
            dt = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Try to parse date formats
        date_formats = [
            '%Y-%m-%d',    # 2024-12-25
            '%m/%d/%Y',    # 12/25/2024
            '%B %d, %Y',    # December 25, 2024
            '%b %d, %Y',    # Dec 25, 2024
            '%d %B %Y',     # 25 December 2024
        ]
        
        date_parsed = False
        for fmt in date_formats:
            try:
                dt = datetime.strptime(time_part, fmt)
                date_parsed = True
                break
            except ValueError:
                pass
        
        # If no date was found in the string, assume today
        if not date_parsed and not (datetime_str.lower().startswith(('today', 'tomorrow'))):
            dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
            time_part = datetime_str

        # Parse time
        time_formats = [
            '%H:%M',        # 14:00
            '%I:%M%p',      # 2:00PM
            '%I%p',         # 2PM
            '%H:%M:%S',     # 14:00:00
            '%I:%M:%S%p',   # 2:00:00PM
        ]
        
        time_match = re.search(r'(\d{1,2}(?::\d{2}){0,2}\s*[ap]m?)|(\d{1,2}:\d{2}(?::\d{2})?)', time_part, re.IGNORECASE)
        if time_match:
            time_str = time_match.group(0)
            for fmt in time_formats:
                try:
                    time = datetime.strptime(time_str, fmt).time()
                    dt = dt.replace(hour=time.hour, minute=time.minute, second=time.second)
                    break
                except ValueError:
                    pass
        
        # If no time was provided, use current time
        if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
            dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second)

        
        
        return dt.isoformat(timespec='seconds')
    
    except Exception as e:
        raise ValueError(f"Could not parse datetime string '{datetime_str}': {str(e)}")


def get_calendar_service():
    """Get authenticated Google Calendar service"""
    creds = None
    
    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # Get new credentials if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for next time
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    
    return build("calendar", "v3", credentials=creds)

@mcp.tool()
async def create_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None
) -> str:
    """
    Use this function to create calendar events in Google Calendar with all necessary details. 

    Key guidelines:
    1. Always provide both summary (event title) and valid start/end times in ISO 8601 format (e.g., "2025-04-29T17:48:07.474522")
    2. The timezone is automatically set to EDT - no need to specify timezone
    3. Include any optional parameters when available:
    - description: More details about the event
    - location: Where the event will take place
    - attendees: List of email addresses to invite
    4. The function returns either a clickable event link (success) or an error message

    Example scenarios when to use:
    - When user wants to schedule a meeting, appointment, or reminder
    - When user provides specific date/time information for an event
    - When user mentions inviting others or adding location/details

    Example usage:
    * "Schedule a team meeting tomorrow from 2-3pm about the Q2 roadmap"
    * "Create an event called 'Dentist Appointment' next Tuesday at 9am for 1 hour"
    * "Add a birthday dinner to my calendar for May 5th at 7pm at Olive Garden"
    """
    try:
        service = get_calendar_service()
        
        event = {
        'summary': summary,
        'start': {
            'dateTime': convert_to_iso_datetime(start_time),
            'timeZone': "EST",
        },
        'end': {
            'dateTime': convert_to_iso_datetime(end_time),
            'timeZone': "EST",
        },
    }
        
        # Add optional fields if provided
        if description:
            event["description"] = description
        if location:
            event["location"] = location
        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]
        
        # Create the event
        created_event = service.events().insert(
            calendarId="primary",
            body=event
        ).execute()
        
        return f"✅ Event created: {created_event.get('htmlLink')}"
    
    except HttpError as error:
        return f"❌ Google API error: {error}"
    except Exception as e:
        return f"❌ Failed to create event: {str(e)}"


# @mcp.tool()
# async def update_event()->str:
#     try:
#         service=get_calendar_service()

#     except HttpError as error:
#         return f"❌ Google API error: {error}"
#     except Exception as e:
#         return f"❌ Failed to update event: {str(e)}"

# @mcp.tool()
# async def delete_event()->str:
#     list_eventIds=[]
    
#     try:
#         service=get_calendar_service()

#     except HttpError as error:
#         return f"❌ Google API error: {error}"
#     except Exception as e:
#         return f"❌ Failed to update event: {str(e)}"


def search_calendar_events(start_time=None, end_time=None, max_results=10):
    """
    Search Google Calendar events within a specified time range.
    
    Args:
        start_time (str): ISO format start time (e.g., "2025-05-01T09:00:00")
        end_time (str): ISO format end time (e.g., "2025-05-01T17:00:00")
        max_results (int): Maximum number of events to return (default: 10)
    
    Returns:
        tuple: (success: bool, result: list/str) 
               Where result is either list of events or error message
    """
    try:

        service = get_calendar_service()

        # Set default time range (current day) if not specified
        now = datetime.utcnow()
        if not start_time:
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
        else:
            # Ensure provided start_time is properly formatted
            if 'Z' not in start_time and '+' not in start_time:
                start_time += 'Z'
        
        if not end_time:
            end_time = (now.replace(hour=23, minute=59, second=59, microsecond=999999) + timedelta(days=1)).isoformat() + 'Z'
        else:
            # Ensure provided end_time is properly formatted
            if 'Z' not in end_time and '+' not in end_time:
                end_time += 'Z'

        # Call the Calendar API
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_time,
            timeMax=end_time,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        
        if not events:
            return (True, [])  # Return empty list rather than error for no events
            
        # Format events data
        formatted_events = []
        for event in events:
            event_data = {
                'summary': event.get('summary', 'No title'),
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'end': event['end'].get('dateTime', event['end'].get('date')),
                'location': event.get('location', 'Not specified'),
                'description': event.get('description', 'None')[:100] + '...' if event.get('description') else 'None'
            }
            formatted_events.append(event_data)
        
        return (True, formatted_events)

    except HttpError as error:
        error_details = error.content.decode('utf-8') if hasattr(error, 'content') else str(error)
        return (False, f"Google Calendar API error: {error_details}")
    except Exception as e:
        return (False, f"Error searching events: {str(e)}")
    

@mcp.tool()
async def search_events(start_time: str = None, end_time: str = None) -> str:
    """
    Searches for calendar events within a specified time range and returns details of matching events.
    
    This function connects to the user's primary Google Calendar and returns events occurring
    between the specified start and end times. If no times are specified, it defaults to the current day.

    Parameters:
    - start_time (str, optional): Start time in ISO format (e.g., "2025-04-30T09:00:00"). 
                                 If not provided, defaults to start of current day.
    - end_time (str, optional): End time in ISO format (e.g., "2025-04-30T17:00:00").
                               If not provided, defaults to end of current day.

    Returns:
    str: A formatted string with event details or an error message. Possible returns:
         - Formatted list of events with their details
         - "No events found between [start] and [end]" if no matches
         - Error message if something went wrong

    Notes:
    - Only searches the primary calendar
    - Returns up to 10 events
    - Events are ordered by start time
    - Both single-day and multi-day events are included if they overlap with the time range

    Example calls:
    - "What are my events today?"
    - "Show me events between April 30 and May 2"
    - "What's on my calendar tomorrow?"
    """
    try:
        # Call the helper function
        success, result = search_calendar_events(start_time, end_time)
        
        if not success:
            return f"❌ {result}"  # Return the error message
        
        if not result:  # Empty list means no events found
            # Format the time range for display
            now = datetime.utcnow()
            display_start = start_time if start_time else now.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d')
            display_end = end_time if end_time else (now.replace(hour=23, minute=59, second=59, microsecond=999999) + timedelta(days=1)).strftime('%Y-%m-%d')
            return f"No events found between {display_start} and {display_end}"
            
        # Format the events into a string response
        response = []
        for event in result:
            event_details = (
                f"Event: {event['summary']}\n"
                f"Time: {event['start']} to {event['end']}\n"
                f"Location: {event['location']}\n"
                f"Description: {event['description']}"
            )
            response.append(event_details)
        
        return "\n\n".join(response) if len(response) > 1 else response[0]

    except Exception as e:
        return f"❌ Unexpected error while searching events: {str(e)}"


if __name__ == "__main__":
    print("📅 Google Calendar Service Starting...", file=sys.stderr)
    mcp.run()
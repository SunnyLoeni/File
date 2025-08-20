#!/usr/bin/env python3
"""
Telegram Account Analyzer Bot - Single File Version
Analyzes Telegram account registration date, country, and other details
"""

import logging
import asyncio
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telethon import TelegramClient
from telethon.tl.functions.users import GetFullUserRequest
from telethon.errors import UserPrivacyRestrictedError, UserNotMutualContactError, FloodWaitError
import io
import os

# ================================
# CONFIGURATION - EDIT THESE VALUES
# ================================

# Get these from @BotFather
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Get these from https://my.telegram.org
API_ID = 12345678  # Your API ID (integer)
API_HASH = "your_api_hash_here"  # Your API Hash (string)

# Optional: Your Telegram user ID for admin features
ADMIN_USER_ID = 123456789

# ================================
# LOGGING CONFIGURATION
# ================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ================================
# MAIN BOT CLASS
# ================================

class TelegramAccountAnalyzer:
    def __init__(self):
        self.client = None
        self.session_initialized = False
        
    async def initialize_client(self):
        """Initialize Telethon client"""
        if self.session_initialized:
            return True
            
        try:
            self.client = TelegramClient('bot_session', API_ID, API_HASH)
            await self.client.start(bot_token=BOT_TOKEN)
            self.session_initialized = True
            logger.info("Telethon client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Telethon client: {e}")
            return False
    
    async def get_user_info(self, user_id):
        """Get comprehensive user information"""
        try:
            if not self.session_initialized:
                if not await self.initialize_client():
                    return {'error': 'Failed to initialize Telegram client'}
            
            # Handle username input
            if isinstance(user_id, str) and not user_id.isdigit():
                if user_id.startswith('@'):
                    user_id = user_id[1:]
            
            # Get user entity
            try:
                user = await self.client.get_entity(user_id)
            except ValueError as e:
                return {'error': f'User not found: {str(e)}'}
            except Exception as e:
                return {'error': f'Failed to get user entity: {str(e)}'}
            
            # Get full user information
            try:
                full_user = await self.client(GetFullUserRequest(user))
            except Exception as e:
                logger.warning(f"Could not get full user info: {e}")
                full_user = None
            
            # Extract and compile user information
            user_info = {
                'id': user.id,
                'first_name': getattr(user, 'first_name', None) or 'N/A',
                'last_name': getattr(user, 'last_name', None) or 'N/A',
                'username': getattr(user, 'username', None) or 'N/A',
                'phone': getattr(user, 'phone', None) or 'Hidden/Private',
                'is_bot': getattr(user, 'bot', False),
                'is_verified': getattr(user, 'verified', False),
                'is_premium': getattr(user, 'premium', False),
                'is_fake': getattr(user, 'fake', False),
                'is_scam': getattr(user, 'scam', False),
                'is_deleted': getattr(user, 'deleted', False),
                'lang_code': getattr(user, 'lang_code', None),
                'dc_id': self._get_dc_id(user),
                'registration_date': self._estimate_registration_date(user.id),
                'country': self._estimate_country(user),
                'status': await self._get_user_status(user),
                'profile_photo': self._has_profile_photo(user),
                'common_chats': self._get_common_chats(full_user),
                'bio': self._get_user_bio(full_user),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            return user_info
            
        except UserPrivacyRestrictedError:
            return {'error': 'User privacy settings prevent access to their information'}
        except UserNotMutualContactError:
            return {'error': 'Cannot access user information - user privacy restrictions'}
        except FloodWaitError as e:
            return {'error': f'Rate limited. Please wait {e.seconds} seconds and try again'}
        except Exception as e:
            logger.error(f"Error getting user info for {user_id}: {e}")
            return {'error': f'Failed to retrieve user information: {str(e)}'}
    
    def _get_dc_id(self, user):
        """Extract data center ID"""
        try:
            if hasattr(user, 'photo') and user.photo:
                return getattr(user.photo, 'dc_id', 'Unknown')
            return 'No Photo'
        except:
            return 'Unknown'
    
    def _estimate_registration_date(self, user_id):
        """Estimate registration date based on user ID patterns"""
        try:
            # Telegram user ID to approximate registration date mapping
            # Based on observed patterns and known milestones
            
            id_ranges = [
                (1000, {'year': 2013, 'month': 8, 'day': 14}),      # Early beta users
                (10000, {'year': 2013, 'month': 9, 'day': 15}),     # Beta expansion
                (100000, {'year': 2013, 'month': 11, 'day': 1}),    # Public beta
                (1000000, {'year': 2014, 'month': 3, 'day': 1}),    # Early 2014
                (10000000, {'year': 2015, 'month': 6, 'day': 1}),   # Mid 2015
                (50000000, {'year': 2016, 'month': 6, 'day': 1}),   # Mid 2016
                (100000000, {'year': 2017, 'month': 1, 'day': 1}),  # Early 2017
                (200000000, {'year': 2017, 'month': 8, 'day': 1}),  # Mid 2017
                (400000000, {'year': 2018, 'month': 6, 'day': 1}),  # Mid 2018
                (600000000, {'year': 2019, 'month': 3, 'day': 1}),  # Early 2019
                (800000000, {'year': 2019, 'month': 9, 'day': 1}),  # Late 2019
                (1000000000, {'year': 2020, 'month': 3, 'day': 1}), # Early 2020
                (1200000000, {'year': 2020, 'month': 8, 'day': 1}), # Mid 2020
                (1400000000, {'year': 2021, 'month': 1, 'day': 1}), # Early 2021
                (1600000000, {'year': 2021, 'month': 6, 'day': 1}), # Mid 2021
                (1800000000, {'year': 2022, 'month': 1, 'day': 1}), # Early 2022
                (2000000000, {'year': 2022, 'month': 6, 'day': 1}), # Mid 2022
                (2200000000, {'year': 2023, 'month': 1, 'day': 1}), # Early 2023
                (2400000000, {'year': 2023, 'month': 6, 'day': 1}), # Mid 2023
                (2600000000, {'year': 2024, 'month': 1, 'day': 1}), # Early 2024
            ]
            
            for threshold, date_info in id_ranges:
                if user_id < threshold:
                    return {**date_info, 'estimated': True, 'accuracy': 'approximate'}
            
            # For very new users
            return {'year': 2024, 'month': 6, 'day': 1, 'estimated': True, 'accuracy': 'approximate'}
                
        except Exception as e:
            logger.error(f"Error estimating registration date: {e}")
            return {'year': 'Unknown', 'month': 'Unknown', 'day': 'Unknown', 'estimated': True, 'accuracy': 'failed'}
    
    def _estimate_country(self, user):
        """Estimate user's country based on available information"""
        try:
            # Try language code first
            if hasattr(user, 'lang_code') and user.lang_code:
                country = self._country_from_lang_code(user.lang_code)
                if country != 'Unknown':
                    return f"{country} (from language)"
            
            # Try phone number pattern (if available)
            if hasattr(user, 'phone') and user.phone:
                country = self._country_from_phone(user.phone)
                if country != 'Unknown':
                    return f"{country} (from phone)"
            
            return 'Unknown (Privacy Protected)'
            
        except Exception as e:
            logger.error(f"Error estimating country: {e}")
            return 'Unknown'
    
    def _country_from_lang_code(self, lang_code):
        """Map language code to likely country/region"""
        lang_country_map = {
            'en': 'English Speaking Region',
            'ru': 'Russia/CIS Countries',
            'es': 'Spain/Latin America',
            'pt': 'Portugal/Brazil',
            'fr': 'France/Francophone Countries',
            'de': 'Germany/DACH Region',
            'it': 'Italy',
            'tr': 'Turkey',
            'ar': 'Arabic Speaking Countries',
            'fa': 'Iran/Persian Speaking',
            'hi': 'India/Hindi Speaking',
            'zh': 'China/Chinese Speaking',
            'ja': 'Japan',
            'ko': 'South Korea',
            'uk': 'Ukraine',
            'pl': 'Poland',
            'nl': 'Netherlands',
            'sv': 'Sweden',
            'da': 'Denmark',
            'no': 'Norway',
            'fi': 'Finland',
            'cs': 'Czech Republic',
            'hu': 'Hungary',
            'ro': 'Romania',
            'bg': 'Bulgaria',
            'hr': 'Croatia',
            'sk': 'Slovakia',
            'sl': 'Slovenia',
            'et': 'Estonia',
            'lv': 'Latvia',
            'lt': 'Lithuania',
            'el': 'Greece',
            'he': 'Israel',
            'th': 'Thailand',
            'vi': 'Vietnam',
            'id': 'Indonesia',
            'ms': 'Malaysia',
            'tl': 'Philippines',
            'bn': 'Bangladesh/Bengal',
            'ur': 'Pakistan/Urdu Speaking',
            'ta': 'Tamil Speaking Regions',
            'te': 'Telugu Speaking Regions',
            'ml': 'Malayalam Speaking Regions',
            'kn': 'Kannada Speaking Regions',
            'gu': 'Gujarati Speaking Regions',
            'pa': 'Punjabi Speaking Regions',
            'ne': 'Nepal',
            'si': 'Sri Lanka',
            'my': 'Myanmar',
            'km': 'Cambodia',
            'lo': 'Laos',
            'ka': 'Georgia',
            'hy': 'Armenia',
            'az': 'Azerbaijan',
            'kk': 'Kazakhstan',
            'ky': 'Kyrgyzstan',
            'uz': 'Uzbekistan',
            'tg': 'Tajikistan',
            'tk': 'Turkmenistan',
            'mn': 'Mongolia',
            'be': 'Belarus',
            'mk': 'North Macedonia',
            'sq': 'Albania',
            'sr': 'Serbia',
            'bs': 'Bosnia and Herzegovina',
            'me': 'Montenegro',
            'is': 'Iceland',
            'mt': 'Malta',
            'ga': 'Ireland',
            'cy': 'Wales',
            'gd': 'Scotland',
            'eu': 'Basque Region',
            'ca': 'Catalonia',
            'gl': 'Galicia',
            'af': 'South Africa/Afrikaans',
            'sw': 'East Africa/Swahili',
            'am': 'Ethiopia',
            'zu': 'South Africa/Zulu',
            'xh': 'South Africa/Xhosa',
            'yo': 'Nigeria/Yoruba',
            'ig': 'Nigeria/Igbo',
            'ha': 'West Africa/Hausa'
        }
        return lang_country_map.get(lang_code.lower(), 'Unknown')
    
    def _country_from_phone(self, phone):
        """Estimate country from phone number (basic patterns)"""
        if not phone or len(phone) < 2:
            return 'Unknown'
        
        # Remove any non-digit characters
        phone_digits = ''.join(filter(str.isdigit, phone))
        
        # Basic country code mapping (most common ones)
        country_codes = {
            '1': 'USA/Canada',
            '7': 'Russia/Kazakhstan',
            '20': 'Egypt',
            '27': 'South Africa',
            '30': 'Greece',
            '31': 'Netherlands',
            '32': 'Belgium',
            '33': 'France',
            '34': 'Spain',
            '36': 'Hungary',
            '39': 'Italy',
            '40': 'Romania',
            '41': 'Switzerland',
            '43': 'Austria',
            '44': 'United Kingdom',
            '45': 'Denmark',
            '46': 'Sweden',
            '47': 'Norway',
            '48': 'Poland',
            '49': 'Germany',
            '51': 'Peru',
            '52': 'Mexico',
            '53': 'Cuba',
            '54': 'Argentina',
            '55': 'Brazil',
            '56': 'Chile',
            '57': 'Colombia',
            '58': 'Venezuela',
            '60': 'Malaysia',
            '61': 'Australia',
            '62': 'Indonesia',
            '63': 'Philippines',
            '64': 'New Zealand',
            '65': 'Singapore',
            '66': 'Thailand',
            '81': 'Japan',
            '82': 'South Korea',
            '84': 'Vietnam',
            '86': 'China',
            '90': 'Turkey',
            '91': 'India',
            '92': 'Pakistan',
            '93': 'Afghanistan',
            '94': 'Sri Lanka',
            '95': 'Myanmar',
            '98': 'Iran',
            '212': 'Morocco',
            '213': 'Algeria',
            '216': 'Tunisia',
            '218': 'Libya',
            '220': 'Gambia',
            '221': 'Senegal',
            '222': 'Mauritania',
            '223': 'Mali',
            '224': 'Guinea',
            '225': 'Ivory Coast',
            '226': 'Burkina Faso',
            '227': 'Niger',
            '228': 'Togo',
            '229': 'Benin',
            '230': 'Mauritius',
            '231': 'Liberia',
            '232': 'Sierra Leone',
            '233': 'Ghana',
            '234': 'Nigeria',
            '235': 'Chad',
            '236': 'Central African Republic',
            '237': 'Cameroon',
            '238': 'Cape Verde',
            '239': 'São Tomé and Príncipe',
            '240': 'Equatorial Guinea',
            '241': 'Gabon',
            '242': 'Republic of the Congo',
            '243': 'Democratic Republic of the Congo',
            '244': 'Angola',
            '245': 'Guinea-Bissau',
            '246': 'British Indian Ocean Territory',
            '248': 'Seychelles',
            '249': 'Sudan',
            '250': 'Rwanda',
            '251': 'Ethiopia',
            '252': 'Somalia',
            '253': 'Djibouti',
            '254': 'Kenya',
            '255': 'Tanzania',
            '256': 'Uganda',
            '257': 'Burundi',
            '258': 'Mozambique',
            '260': 'Zambia',
            '261': 'Madagascar',
            '262': 'Réunion',
            '263': 'Zimbabwe',
            '264': 'Namibia',
            '265': 'Malawi',
            '266': 'Lesotho',
            '267': 'Botswana',
            '268': 'Eswatini',
            '269': 'Comoros',
            '290': 'Saint Helena',
            '291': 'Eritrea',
            '297': 'Aruba',
            '298': 'Faroe Islands',
            '299': 'Greenland',
            '350': 'Gibraltar',
            '351': 'Portugal',
            '352': 'Luxembourg',
            '353': 'Ireland',
            '354': 'Iceland',
            '355': 'Albania',
            '356': 'Malta',
            '357': 'Cyprus',
            '358': 'Finland',
            '359': 'Bulgaria',
            '370': 'Lithuania',
            '371': 'Latvia',
            '372': 'Estonia',
            '373': 'Moldova',
            '374': 'Armenia',
            '375': 'Belarus',
            '376': 'Andorra',
            '377': 'Monaco',
            '378': 'San Marino',
            '380': 'Ukraine',
            '381': 'Serbia',
            '382': 'Montenegro',
            '383': 'Kosovo',
            '385': 'Croatia',
            '386': 'Slovenia',
            '387': 'Bosnia and Herzegovina',
            '389': 'North Macedonia',
            '420': 'Czech Republic',
            '421': 'Slovakia',
            '423': 'Liechtenstein',
            '500': 'Falkland Islands',
            '501': 'Belize',
            '502': 'Guatemala',
            '503': 'El Salvador',
            '504': 'Honduras',
            '505': 'Nicaragua',
            '506': 'Costa Rica',
            '507': 'Panama',
            '508': 'Saint Pierre and Miquelon',
            '509': 'Haiti',
            '590': 'Guadeloupe',
            '591': 'Bolivia',
            '592': 'Guyana',
            '593': 'Ecuador',
            '594': 'French Guiana',
            '595': 'Paraguay',
            '596': 'Martinique',
            '597': 'Suriname',
            '598': 'Uruguay',
            '599': 'Netherlands Antilles',
            '670': 'East Timor',
            '672': 'Australian External Territories',
            '673': 'Brunei',
            '674': 'Nauru',
            '675': 'Papua New Guinea',
            '676': 'Tonga',
            '677': 'Solomon Islands',
            '678': 'Vanuatu',
            '679': 'Fiji',
            '680': 'Palau',
            '681': 'Wallis and Futuna',
            '682': 'Cook Islands',
            '683': 'Niue',
            '684': 'American Samoa',
            '685': 'Samoa',
            '686': 'Kiribati',
            '687': 'New Caledonia',
            '688': 'Tuvalu',
            '689': 'French Polynesia',
            '690': 'Tokelau',
            '691': 'Federated States of Micronesia',
            '692': 'Marshall Islands',
            '850': 'North Korea',
            '852': 'Hong Kong',
            '853': 'Macau',
            '855': 'Cambodia',
            '856': 'Laos',
            '880': 'Bangladesh',
            '886': 'Taiwan',
            '960': 'Maldives',
            '961': 'Lebanon',
            '962': 'Jordan',
            '963': 'Syria',
            '964': 'Iraq',
            '965': 'Kuwait',
            '966': 'Saudi Arabia',
            '967': 'Yemen',
            '968': 'Oman',
            '970': 'Palestine',
            '971': 'United Arab Emirates',
            '972': 'Israel',
            '973': 'Bahrain',
            '974': 'Qatar',
            '975': 'Bhutan',
            '976': 'Mongolia',
            '977': 'Nepal',
            '992': 'Tajikistan',
            '993': 'Turkmenistan',
            '994': 'Azerbaijan',
            '995': 'Georgia',
            '996': 'Kyrgyzstan',
            '998': 'Uzbekistan'
        }
        
        # Try different lengths for country codes
        for length in [3, 2, 1]:
            if len(phone_digits) >= length:
                code = phone_digits[:length]
                if code in country_codes:
                    return country_codes[code]
        
        return 'Unknown'
    
    async def _get_user_status(self, user):
        """Get user's last seen status"""
        try:
            if hasattr(user, 'status'):
                status = user.status
                status_type = type(status).__name__
                
                if hasattr(status, 'was_online'):
                    last_seen = status.was_online
                    now = datetime.now()
                    
                    # Calculate time difference
                    if isinstance(last_seen, datetime):
                        diff = now - last_seen.replace(tzinfo=None)
                        
                        if diff.days > 365:
                            return f"Last seen: {diff.days // 365} year(s) ago"
                        elif diff.days > 30:
                            return f"Last seen: {diff.days // 30} month(s) ago"
                        elif diff.days > 0:
                            return f"Last seen: {diff.days} day(s) ago"
                        elif diff.seconds > 3600:
                            return f"Last seen: {diff.seconds // 3600} hour(s) ago"
                        elif diff.seconds > 60:
                            return f"Last seen: {diff.seconds // 60} minute(s) ago"
                        else:
                            return "Last seen: Recently"
                    else:
                        return f"Last seen: {last_seen}"
                
                elif 'Online' in status_type:
                    return "🟢 Online"
                elif 'Recently' in status_type:
                    return "🟡 Recently"
                elif 'LastWeek' in status_type:
                    return "🟠 Within a week"
                elif 'LastMonth' in status_type:
                    return "🔴 Within a month"
                elif 'Long' in status_type:
                    return "⚫ Long time ago"
                else:
                    return f"Status: {status_type.replace('UserStatus', '')}"
            
            return "Unknown"
            
        except Exception as e:
            logger.error(f"Error getting user status: {e}")
            return "Unknown"
    
    def _has_profile_photo(self, user):
        """Check if user has profile photo"""
        try:
            return "Yes" if hasattr(user, 'photo') and user.photo else "No"
        except:
            return "Unknown"
    
    def _get_common_chats(self, full_user):
        """Get number of common chats"""
        try:
            if full_user and hasattr(full_user, 'full_user'):
                return getattr(full_user.full_user, 'common_chats_count', 0)
            return 0
        except:
            return 0
    
    def _get_user_bio(self, full_user):
        """Get user's bio/about"""
        try:
            if full_user and hasattr(full_user, 'full_user'):
                bio = getattr(full_user.full_user, 'about', '')
                return bio[:100] + '...' if len(bio) > 100 else bio or 'No bio'
            return 'No bio'
        except:
            return 'No bio'

# ================================
# BOT HANDLERS
# ================================

# Initialize analyzer
analyzer = TelegramAccountAnalyzer()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    welcome_message = f"""
🔍 **Telegram Account Analyzer Bot**

Hello {user.first_name}! I can analyze Telegram accounts and provide detailed information.

**🚀 Quick Start:**
• Send `/analyze <user_id>` - Analyze any user
• Send `/myinfo` - Analyze your account
• Forward a message - Auto-analyze sender
• Reply to message with `/analyze`

**📊 Information Provided:**
✅ Registration date estimation
✅ Country/region detection  
✅ Account verification status
✅ Premium status
✅ Data center location
✅ Last seen status
✅ Account security flags

**📋 Available Commands:**
• `/start` - Show this message
• `/help` - Detailed help
• `/analyze <id>` - Analyze user
• `/myinfo` - Your account info
• `/stats` - Bot statistics

**⚠️ Privacy Notice:**
This bot respects user privacy settings. Some information may be limited or unavailable based on user privacy configurations.

Ready to analyze? Try `/myinfo` to see your own account details!
    """
    
    keyboard = [
        [
            InlineKeyboardButton("📊 My Account", callback_data="analyze_self"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ],
        [
            InlineKeyboardButton("📋 Commands", callback_data="commands"),
            InlineKeyboardButton("📈 Stats", callback_data="stats")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detailed help command"""
    help_text = """
🆘 **Detailed Help Guide**

**🎯 How to Use:**

**Method 1: Direct Analysis**
• Use `/analyze <user_id>` or `/analyze @username`
• Example: `/analyze 123456789` or `/analyze @ExampleUser`

**Method 2: Self Analysis**
• Use `/myinfo` to analyze your own account

**Method 3: Message-based Analysis**
• Reply to any message with `/analyze`
• Forward a message and I'll analyze the sender

**📋 All Commands:**
• `/start` - Start bot and show welcome message
• `/help` - Show this detailed help
• `/analyze <id>` - Analyze a specific user
• `/myinfo` - Show your account details
• `/stats` - View bot usage statistics
• `/clear` - Clear bot session (admin only)

**🔐 Privacy Notes:**
• Some information may be restricted due to user privacy settings
• Phone numbers are only visible if you're a contact
• The bot never stores sensitive information

**⚠️ Limitations:**
• Registration dates are estimated based on user ID patterns
• Country detection is approximate, based on language or phone
• Some details may be unavailable due to privacy settings

Need help? Contact the bot admin or try `/start` to begin!
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def myinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze the user's own account"""
    user_id = update.effective_user.id
    user_info = await analyzer.get_user_info(user_id)
    
    if 'error' in user_info:
        await update.message.reply_text(f"❌ Error: {user_info['error']}")
        return
    
    message = format_user_info(user_info)
    await update.message.reply_text(message, parse_mode='Markdown')

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze a specific user"""
    user_id = None
    
    # Check if command is used in reply to a message
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
    elif context.args:
        user_id = context.args[0]
    
    if not user_id:
        await update.message.reply_text(
            "❌ Please provide a user ID, username, or reply to a message\n"
            "Example: `/analyze 123456789` or `/analyze @username`",
            parse_mode='Markdown'
        )
        return
    
    user_info = await analyzer.get_user_info(user_id)
    
    if 'error' in user_info:
        await update.message.reply_text(f"❌ Error: {user_info['error']}")
        return
    
    message = format_user_info(user_info)
    await update.message.reply_text(message, parse_mode='Markdown')

async def forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze sender of forwarded message"""
    if update.message.forward_from:
        user_id = update.message.forward_from.id
        user_info = await analyzer.get_user_info(user_id)
        
        if 'error' in user_info:
            await update.message.reply_text(f"❌ Error: {user_info['error']}")
            return
        
        message = format_user_info(user_info)
        await update.message.reply_text(message, parse_mode='Markdown')
    else:
        await update.message.reply_text(
            "❌ This message wasn't forwarded from a user I can analyze.\n"
            "Please forward a message from a user or use /analyze <user_id>",
            parse_mode='Markdown'
        )

def format_user_info(user_info):
    """Format user information into a readable message"""
    reg_date = user_info['registration_date']
    date_str = f"{reg_date['year']}-{reg_date['month']:02d}-{reg_date['day']:02d} (Estimated)"
    
    message = f"""
🔍 **User Analysis Report**

**🆔 User ID:** {user_info['id']}
**👤 Name:** {user_info['first_name']} {user_info['last_name']}
**📛 Username:** {user_info['username']}
**📱 Phone:** {user_info['phone']}
**🤖 Is Bot:** {'Yes' if user_info['is_bot'] else 'No'}
**✅ Verified:** {'Yes' if user_info['is_verified'] else 'No'}
**🌟 Premium:** {'Yes' if user_info['is_premium'] else 'No'}
**⚠️ Fake/Scam:** {'Yes' if user_info['is_fake'] or user_info['is_scam'] else 'No'}
**🗑️ Deleted:** {'Yes' if user_info['is_deleted'] else 'No'}
**🌐 Language:** {user_info['lang_code'] or 'Unknown'}
**🌍 Country:** {user_info['country']}
**📅 Registration:** {date_str}
**🖼️ Profile Photo:** {user_info['profile_photo']}
**👥 Common Chats:** {user_info['common_chats']}
**📜 Bio:** {user_info['bio']}
**📍 Data Center:** {user_info['dc_id']}
**🕒 Last Seen:** {user_info['status']}
**⏰ Analyzed At:** {user_info['analysis_timestamp']}

⚠️ *Note:* Some information may be approximate or limited due to privacy settings.
    """
    return message

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics (placeholder)"""
    await update.message.reply_text(
        "📈 **Bot Statistics**\n\n"
        "This feature is under development.\n"
        "It will show usage statistics and analysis history.",
        parse_mode='Markdown'
    )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear bot session (admin only)"""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Access denied: Admin only command")
        return
    
    try:
        if os.path.exists('bot_session.session'):
            os.remove('bot_session.session')
            analyzer.session_initialized = False
            await update.message.reply_text("✅ Bot session cleared successfully")
        else:
            await update.message.reply_text("ℹ️ No session file found")
    except Exception as e:
        await update.message.reply_text(f"❌ Error clearing session: {str(e)}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "analyze_self":
        user_id = query.from_user.id
        user_info = await analyzer.get_user_info(user_id)
        
        if 'error' in user_info:
            await query.message.reply_text(f"❌ Error: {user_info['error']}")
            return
        
        message = format_user_info(user_info)
        await query.message.reply_text(message, parse_mode='Markdown')
    
    elif query.data == "help":
        await help_command(query, context)
    
    elif query.data == "commands":
        await query.message.reply_text(
            "📋 **Available Commands:**\n\n"
            "• `/start` - Start bot\n"
            "• `/help` - Detailed help\n"
            "• `/analyze <id>` - Analyze user\n"
            "• `/myinfo` - Your account info\n"
            "• `/stats` - Bot statistics\n"
            "• `/clear` - Clear session (admin)",
            parse_mode='Markdown'
        )
    
    elif query.data == "stats":
        await stats(query, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and hasattr(update, 'message'):
        await update.message.reply_text(
            "❌ An error occurred. Please try again later or contact the bot admin.",
            parse_mode='Markdown'
        )

# ================================
# MAIN FUNCTION
# ================================

def main():
    """Run the bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze))
    application.add_handler(CommandHandler("myinfo", myinfo))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("clear", clear))
    
    # Message handler for forwarded messages
    application.add_handler(MessageHandler(filters.FORWARDED, forwarded_message))
    
    # Callback handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

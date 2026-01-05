"""
Data Collection Service for MinerSentinel Dashboard
Polls Bitaxe and Avalon devices and CKPool/PublicPool periodically and stores data in Postgres.
Settings are loaded from the database (collector_settings table).
"""

import logging
import os
import time
from datetime import datetime

import psycopg2
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from collectors.avalon_collector import AvalonCollector
from collectors.bitaxe_collector import BitAxeCollector
from collectors.ckpool_collector import collect_ckpool_data
from collectors.publicpool_collector import collect_publicpool_data
from decouple import config
from flask import Flask, jsonify
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Database Configuration
POSTGRES_DB = config('POSTGRES_DB', default='minersentinel')
POSTGRES_USER = config('POSTGRES_USER', default='minersentinel')
POSTGRES_PASSWORD = config('POSTGRES_PASSWORD', default='changeme')
POSTGRES_HOST = config('POSTGRES_HOST', default='postgres')
POSTGRES_PORT = config('POSTGRES_PORT', default='5432')

# Build DATABASE_URL from components
DATABASE_URL = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'

# Global settings cache (loaded from database)
collector_settings = {
    'polling_interval_minutes': 15,
    'device_check_interval_minutes': 5,
    'pool_type': 'ckpool',
    'ckpool_address': '',
    'ckpool_url': 'https://eusolo.ckpool.org',
    'publicpool_address': '',
    'publicpool_url': 'http://localhost:3334',
    'telegram_enabled': False,
    'telegram_bot_token': '',
    'telegram_chat_id': '',
}

# Initialize collectors (will load devices from database)
bitaxe_collector = BitAxeCollector(DATABASE_URL)
avalon_collector = AvalonCollector(DATABASE_URL)

# Scheduler
scheduler = BackgroundScheduler()


def load_settings_from_database():
    """Load collector settings from the database."""
    global collector_settings
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT polling_interval_minutes, device_check_interval_minutes,
                   pool_type, ckpool_address, ckpool_url,
                   publicpool_address, publicpool_url,
                   telegram_enabled, telegram_bot_token, telegram_chat_id
            FROM collector_settings
            WHERE id = 1
        """)
        row = cursor.fetchone()

        if row:
            collector_settings = dict(row)
            logger.info(f"Loaded settings from database: polling={collector_settings['polling_interval_minutes']}min, "
                       f"device_check={collector_settings['device_check_interval_minutes']}min, "
                       f"pool_type={collector_settings.get('pool_type', 'ckpool')}")
        else:
            logger.warning("No settings found in database, using defaults")

        cursor.close()
        conn.close()
        return collector_settings
    except Exception as e:
        logger.error(f"Error loading settings from database: {e}", exc_info=True)
        return collector_settings


def load_active_devices():
    """Load active devices from database and update collectors."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Load Bitaxe devices
        cursor.execute("""
            SELECT device_id, device_name, ip_address
            FROM bitaxe_devices
            WHERE is_active = TRUE
        """)
        bitaxe_devices = cursor.fetchall()
        bitaxe_collector.update_devices(bitaxe_devices)
        logger.info(f"Loaded {len(bitaxe_devices)} active Bitaxe devices")

        # Load Avalon devices
        cursor.execute("""
            SELECT device_id, device_name, ip_address
            FROM avalon_devices
            WHERE is_active = TRUE
        """)
        avalon_devices = cursor.fetchall()
        avalon_collector.update_devices(avalon_devices)
        logger.info(f"Loaded {len(avalon_devices)} active Avalon devices")

        cursor.close()
        conn.close()

        return bitaxe_devices, avalon_devices
    except Exception as e:
        logger.error(f"Error loading devices from database: {e}", exc_info=True)
        return [], []


def poll_all_sources():
    """Poll all data sources and store in database."""
    logger.info("Starting data collection cycle")

    # Reload settings from database (in case they changed)
    load_settings_from_database()

    # Reload devices from database before each collection
    load_active_devices()

    try:
        # Poll Bitaxe devices
        logger.info("Polling Bitaxe devices...")
        bitaxe_collector.collect_all_devices()
        logger.info("Bitaxe polling completed")
    except Exception as e:
        logger.error(f"Error polling Bitaxe devices: {e}", exc_info=True)

    try:
        # Poll Avalon devices
        logger.info("Polling Avalon devices...")
        avalon_collector.collect_all_devices()
        logger.info("Avalon polling completed")
    except Exception as e:
        logger.error(f"Error polling Avalon devices: {e}", exc_info=True)

    # Poll pool statistics based on pool_type setting
    pool_type = collector_settings.get('pool_type', 'ckpool')

    try:
        if pool_type == 'publicpool':
            # Poll PublicPool statistics
            publicpool_address = collector_settings.get('publicpool_address', '')
            if publicpool_address:
                logger.info(f"Polling PublicPool statistics for address: {publicpool_address[:10]}...")
                conn = psycopg2.connect(DATABASE_URL)
                collect_publicpool_data(
                    conn,
                    publicpool_address,
                    collector_settings.get('publicpool_url', 'http://localhost:3334')
                )
                conn.close()
                logger.info("PublicPool polling completed")
            else:
                logger.info("Skipping PublicPool polling - no address configured")
        else:
            # Poll CKPool statistics (default)
            ckpool_address = collector_settings.get('ckpool_address', '')
            if ckpool_address:
                logger.info(f"Polling CKPool statistics for address: {ckpool_address[:10]}...")
                conn = psycopg2.connect(DATABASE_URL)
                collect_ckpool_data(conn, ckpool_address, collector_settings.get('ckpool_url', 'https://eusolo.ckpool.org'))
                conn.close()
                logger.info("CKPool polling completed")
            else:
                logger.info("Skipping CKPool polling - no address configured")
    except Exception as e:
        logger.error(f"Error polling pool ({pool_type}): {e}", exc_info=True)

    logger.info("Data collection cycle completed")


def reschedule_jobs():
    """Reschedule jobs based on current settings from database."""
    global collector_settings

    # Remove existing jobs
    for job in scheduler.get_jobs():
        job.remove()

    polling_interval = collector_settings.get('polling_interval_minutes', 15)
    device_check_interval = collector_settings.get('device_check_interval_minutes', 5)

    # Schedule periodic polling
    scheduler.add_job(
        func=poll_all_sources,
        trigger=IntervalTrigger(minutes=polling_interval),
        id='poll_all_sources',
        name='Poll all data sources',
        replace_existing=True
    )

    # Schedule periodic device check (reload devices more frequently)
    scheduler.add_job(
        func=load_active_devices,
        trigger=IntervalTrigger(minutes=device_check_interval),
        id='check_devices',
        name='Check for new devices',
        replace_existing=True
    )

    # Schedule settings reload (check for settings changes every 2 minutes)
    scheduler.add_job(
        func=check_and_apply_settings_changes,
        trigger=IntervalTrigger(minutes=2),
        id='check_settings',
        name='Check for settings changes',
        replace_existing=True
    )

    logger.info(f"Scheduled jobs: polling every {polling_interval}min, device check every {device_check_interval}min")


def check_and_apply_settings_changes():
    """Check if settings have changed and reschedule if needed."""
    global collector_settings

    old_polling = collector_settings.get('polling_interval_minutes', 15)
    old_device_check = collector_settings.get('device_check_interval_minutes', 5)

    # Reload settings
    load_settings_from_database()

    new_polling = collector_settings.get('polling_interval_minutes', 15)
    new_device_check = collector_settings.get('device_check_interval_minutes', 5)

    # If intervals changed, reschedule jobs
    if old_polling != new_polling or old_device_check != new_device_check:
        logger.info(f"Settings changed: polling {old_polling}->{new_polling}min, device_check {old_device_check}->{new_device_check}min")
        reschedule_jobs()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'data-collection',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/poll', methods=['POST'])
def trigger_poll():
    """Manually trigger a poll cycle."""
    logger.info("Manual poll triggered via API")
    poll_all_sources()
    return jsonify({
        'status': 'success',
        'message': 'Poll cycle completed',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/status', methods=['GET'])
def status():
    """Get service status and next run time."""
    jobs = scheduler.get_jobs()
    poll_job = next((j for j in jobs if j.id == 'poll_all_sources'), None)
    next_run = poll_job.next_run_time if poll_job else None

    # Get current device counts from database
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("SELECT COUNT(*) as count FROM bitaxe_devices WHERE is_active = TRUE")
        bitaxe_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM avalon_devices WHERE is_active = TRUE")
        avalon_count = cursor.fetchone()['count']

        cursor.execute("SELECT device_name, ip_address FROM bitaxe_devices WHERE is_active = TRUE")
        bitaxe_list = cursor.fetchall()

        cursor.execute("SELECT device_name, ip_address FROM avalon_devices WHERE is_active = TRUE")
        avalon_list = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            'status': 'running',
            'polling_interval_minutes': collector_settings.get('polling_interval_minutes', 15),
            'device_check_interval_minutes': collector_settings.get('device_check_interval_minutes', 5),
            'ckpool_address': collector_settings.get('ckpool_address', ''),
            'ckpool_url': collector_settings.get('ckpool_url', 'https://eusolo.ckpool.org'),
            'next_run': next_run.isoformat() if next_run else None,
            'bitaxe_devices_count': bitaxe_count,
            'avalon_devices_count': avalon_count,
            'bitaxe_devices': [{'name': d['device_name'], 'ip': d['ip_address']} for d in bitaxe_list],
            'avalon_devices': [{'name': d['device_name'], 'ip': d['ip_address']} for d in avalon_list]
        })
    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        return jsonify({
            'status': 'running',
            'polling_interval_minutes': collector_settings.get('polling_interval_minutes', 15),
            'next_run': next_run.isoformat() if next_run else None,
            'error': 'Could not fetch device information'
        })


@app.route('/settings/reload', methods=['POST'])
def reload_settings():
    """Manually reload settings from database and reschedule jobs."""
    logger.info("Manual settings reload triggered via API")
    load_settings_from_database()
    reschedule_jobs()
    return jsonify({
        'status': 'success',
        'message': 'Settings reloaded and jobs rescheduled',
        'settings': collector_settings,
        'timestamp': datetime.utcnow().isoformat()
    })


if __name__ == '__main__':
    logger.info("Starting Data Collection Service")

    # Wait for database to be ready
    logger.info("Waiting for database connection...")
    max_retries = 30
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(DATABASE_URL)
            conn.close()
            logger.info("Database connection established")
            break
        except psycopg2.OperationalError:
            if i < max_retries - 1:
                logger.info(f"Database not ready, retrying in 2 seconds... ({i+1}/{max_retries})")
                time.sleep(2)
            else:
                logger.error("Could not connect to database after maximum retries")
                raise

    # Load settings from database
    logger.info("Loading settings from database...")
    load_settings_from_database()
    polling_interval = collector_settings.get('polling_interval_minutes', 15)
    device_check_interval = collector_settings.get('device_check_interval_minutes', 5)
    logger.info(f"Polling interval: {polling_interval} minutes")
    logger.info(f"Device check interval: {device_check_interval} minutes")

    # Load active devices from database
    logger.info("Loading active devices from database...")
    bitaxe_devices, avalon_devices = load_active_devices()
    logger.info(f"Found {len(bitaxe_devices)} Bitaxe and {len(avalon_devices)} Avalon devices")

    # Run initial poll
    logger.info("Running initial data collection...")
    poll_all_sources()

    # Schedule jobs using settings from database
    reschedule_jobs()

    scheduler.start()
    logger.info("Scheduler started")

    # Run Flask app
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()


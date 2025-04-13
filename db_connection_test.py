#!/usr/bin/env python
"""
Database Connection Tester Script

This script tests connection to the Supabase PostgreSQL database and diagnoses common issues.
Run this script to verify your database credentials and troubleshoot connection problems.

Usage:
    python db_connection_test.py
"""
import os
import sys
import time
import socket
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('db_connection.log')
    ]
)
logger = logging.getLogger('db_connection_test')

# SQL query to test if we can actually read from the database
TEST_QUERY = "SELECT 1 AS connection_test;"

def check_connectivity(host, port):
    """Check if we can reach the database server"""
    logger.info(f"Testing network connectivity to {host}:{port}...")
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, int(port)))
        connect_time = time.time() - start_time
        
        if result == 0:
            logger.info(f"✅ Successfully connected to {host}:{port} in {connect_time:.2f} seconds")
            sock.close()
            return True
        else:
            logger.error(f"❌ Failed to connect to {host}:{port} - Connection refused or timed out")
            return False
    except socket.gaierror:
        logger.error(f"❌ Could not resolve hostname: {host}")
        return False
    except Exception as e:
        logger.error(f"❌ Connection error: {str(e)}")
        return False

def test_db_connection():
    """Test connection to Supabase PostgreSQL database"""
    # Get database configuration
    # Production settings
    DB_NAME = "postgres"
    DB_USER = "postgres.skgnsidivjplhlletkvb"
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = "aws-0-us-east-1.pooler.supabase.com"
    DB_PORT = "6543"
    
    # Development settings (fallback)
    if not DB_PASSWORD:
        DB_NAME = os.getenv("PGDATABASE")
        DB_USER = os.getenv("PGUSER")
        DB_PASSWORD = os.getenv("PGPASSWORD")
        DB_HOST = os.getenv("PGHOST")
        DB_PORT = "5432"
    
    # Check if we have credentials
    if not all([DB_NAME, DB_USER, DB_PASSWORD, DB_HOST]):
        logger.error("❌ Missing database credentials. Please check your environment variables.")
        logger.info("Required variables: DB_PASSWORD (production) or PGDATABASE, PGUSER, PGPASSWORD, PGHOST (development)")
        return False
    
    # First, check network connectivity
    if not check_connectivity(DB_HOST, DB_PORT):
        return False
    
    # Now try actual database connection
    try:
        logger.info(f"Testing database connection to {DB_HOST}:{DB_PORT}...")
        
        # Try importing psycopg2
        try:
            import psycopg2
        except ImportError:
            logger.error("❌ Could not import psycopg2. Please install it with: pip install psycopg2-binary")
            return False
        
        # Establish connection
        start_time = time.time()
        connection = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            connect_timeout=10,
            sslmode="require"
        )
        connect_time = time.time() - start_time
        
        # Test a simple query
        cursor = connection.cursor()
        cursor.execute(TEST_QUERY)
        result = cursor.fetchone()
        
        if result and result[0] == 1:
            logger.info(f"✅ Successfully connected to database and executed query in {connect_time:.2f} seconds")
            
            # Get database server version
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            logger.info(f"✅ Database server: {version}")
            
            # Close connection
            cursor.close()
            connection.close()
            return True
        else:
            logger.error("❌ Connected to database but test query failed")
            return False
            
    except psycopg2.OperationalError as e:
        # Most common connection errors
        error_message = str(e)
        
        if "password authentication failed" in error_message or "Wrong password" in error_message:
            logger.error("❌ Authentication failed: Wrong password")
            logger.info("Please check that your DB_PASSWORD environment variable is correct")
        elif "role" in error_message and "does not exist" in error_message:
            logger.error("❌ Authentication failed: User does not exist")
            logger.info("Please check that your database username is correct")
        elif "could not translate host" in error_message:
            logger.error("❌ Could not resolve database hostname")
            logger.info(f"Unable to resolve: {DB_HOST}")
        elif "Connection refused" in error_message:
            logger.error("❌ Connection refused by the server")
            logger.info("Please check that your database host and port are correct and that the server is running")
        elif "timeout expired" in error_message:
            logger.error("❌ Connection timeout")
            logger.info("Database server is not responding within the timeout period")
        else:
            logger.error(f"❌ Database connection error: {error_message}")
        
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting database connection test...")
    success = test_db_connection()
    if success:
        logger.info("✅ All database connection tests passed")
        sys.exit(0)
    else:
        logger.error("❌ Database connection test failed. Check the log for details.")
        sys.exit(1)

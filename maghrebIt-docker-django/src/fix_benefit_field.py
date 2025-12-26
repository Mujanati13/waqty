#!/usr/bin/env python
"""
Script to fix the benefit column in bondecommande table
Run this from the src directory: python fix_benefit_field.py
"""

import os
import sys
import django

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maghrebIt_backend.settings')
django.setup()

from django.db import connection

def fix_benefit_column():
    """
    Modify the benefit column to TEXT type to allow storing commission data
    """
    try:
        with connection.cursor() as cursor:
            print("🔧 Modifying benefit column to TEXT type...")
            
            # Modify the column to TEXT
            cursor.execute("ALTER TABLE `bondecommande` MODIFY COLUMN `benefit` TEXT NULL")
            
            print("✅ Successfully modified benefit column to TEXT type!")
            print("📊 You can now store commission data in format: 'percentage|amount'")
            
            # Verify the change
            cursor.execute("""
                SELECT COLUMN_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'bondecommande' 
                AND COLUMN_NAME = 'benefit'
                AND TABLE_SCHEMA = DATABASE()
            """)
            
            result = cursor.fetchone()
            if result:
                print(f"✓ Current column type: {result[0]}")
            
    except Exception as e:
        print(f"❌ Error modifying column: {e}")
        print("\nYou can manually run this SQL command:")
        print("ALTER TABLE `bondecommande` MODIFY COLUMN `benefit` TEXT NULL;")
        sys.exit(1)

if __name__ == '__main__':
    fix_benefit_column()

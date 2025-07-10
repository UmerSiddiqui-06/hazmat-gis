# MySQL Migration Guide

This project has been converted from SQLite to MySQL. Follow these steps to set up your MySQL database:

## Prerequisites

1. MySQL Server installed and running
2. Python environment with pip

## Installation Steps

### 1. Install Dependencies

**On Windows:**
```bash
install_mysql.bat
```

**On Linux/Mac:**
```bash
chmod +x install_mysql.sh
./install_mysql.sh
```

**Or manually:**
```bash
pip install mysql-connector-python python-decouple
```

### 2. Configure Environment Variables

Edit the `.env` file in the project root:

```env
DB_HOST=your_mysql_host          # e.g., localhost
DB_PORT=3306                     # default MySQL port
DB_NAME=your_database_name       # e.g., hazmat_gis
DB_USER=your_username           # your MySQL username
DB_PASSWORD=your_password       # your MySQL password
```

### 3. Create Database Schema

1. Create a new database in MySQL:
   ```sql
   CREATE DATABASE hazmat_gis;
   ```

2. Run the schema file to create tables:
   ```bash
   mysql -u your_username -p hazmat_gis < mysql_schema.sql
   ```

   Or import the `mysql_schema.sql` file using phpMyAdmin or MySQL Workbench.

## Changes Made

### Code Changes
- Replaced `sqlite3` with `mysql.connector`
- Updated connection string to use environment variables
- Changed SQL parameter placeholders from `?` to `%s`
- Updated BOOLEAN data types for MySQL compatibility
- Replaced SQLite's `PRAGMA table_info()` with MySQL's `SHOW COLUMNS`

### Files Modified
- `utitlity.py`: Complete database layer conversion
- `requirements.txt`: Added MySQL connector dependency

### Files Added
- `.env`: Environment configuration template
- `mysql_schema.sql`: Database schema for MySQL
- `install_mysql.bat/sh`: Installation scripts
- `README_MYSQL.md`: This documentation

## Database Migration

If you have existing SQLite data, you'll need to:

1. Export data from SQLite
2. Transform the data format if needed
3. Import into MySQL

The application will create default admin users and settings on first run.

## Troubleshooting

### Connection Issues
- Verify MySQL server is running
- Check credentials in `.env` file
- Ensure database exists
- Verify firewall settings for remote connections

### Import Errors
- Make sure `mysql-connector-python` is installed
- Check Python path and virtual environment

### Database Errors
- Verify MySQL user permissions
- Check database name spelling
- Ensure tables are created correctly

## Default Admin Account

The application creates a default admin account:
- Email: admin
- Password: 0000

Make sure to change this password after first login.

@echo off
REM Installation script for MySQL conversion

echo Installing MySQL connector...
pip install mysql-connector-python python-decouple

echo MySQL dependencies installed successfully!
echo.
echo Please configure your .env file with the following variables:
echo DB_HOST=your_mysql_host
echo DB_PORT=3306
echo DB_NAME=your_database_name
echo DB_USER=your_username
echo DB_PASSWORD=your_password
echo.
echo Make sure your MySQL server is running and the database exists before running the application.
pause

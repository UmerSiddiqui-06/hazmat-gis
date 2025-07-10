-- MySQL Database Schema for HazMat GIS Application
-- Run this script on your MySQL server to create the database structure

-- Create database (optional, you can create this manually)
-- CREATE DATABASE hazmat_gis;
-- USE hazmat_gis;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    email VARCHAR(255),  
    password VARCHAR(255),
    chatgpt BOOLEAN,
    status VARCHAR(255),
    ChatGpt_used INTEGER,
    ChatGpt_limit INTEGER,
    last_reset_date DATETIME,
    chatgptlimittype VARCHAR(255),
    is_admin BOOLEAN,
    allow_download BOOLEAN DEFAULT 0
);

-- Create gpt_limit table
CREATE TABLE IF NOT EXISTS gpt_limit (
    chatgpt BOOLEAN,
    chatgpt_limit INTEGER,
    enable_download BOOLEAN DEFAULT 0
);

-- Create temporary_password table
CREATE TABLE IF NOT EXISTS temporary_password(
    email VARCHAR(255),
    is_temporary BOOLEAN
);

-- Create login_history table
CREATE TABLE IF NOT EXISTS login_history(
    email VARCHAR(255),
    time DATETIME                        
);

-- Create download_history table
CREATE TABLE IF NOT EXISTS download_history(
    Email VARCHAR(255),
    Time DATETIME,
    Type VARCHAR(255),
    Category VARCHAR(255),
    Country VARCHAR(255),
    Impact VARCHAR(255),
    Severity VARCHAR(255),
    Date VARCHAR(255)            
);

-- Create gpt_history table
CREATE TABLE IF NOT EXISTS gpt_history(
    email VARCHAR(255),
    link TEXT,
    title TEXT,
    time DATETIME
);

-- Create gpt_responses table
CREATE TABLE IF NOT EXISTS gpt_responses(
    Link VARCHAR(255),
    Response TEXT
);

-- Insert default data
INSERT INTO gpt_limit (chatgpt, chatgpt_limit, enable_download) VALUES (1, 5, 0);

INSERT INTO temporary_password (email, is_temporary) VALUES ('temp4', TRUE);

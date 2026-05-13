-- Drop tables if they exist to start fresh
DROP TABLE IF EXISTS execution_logs CASCADE;
DROP TABLE IF EXISTS leave_requests CASCADE;
DROP TABLE IF EXISTS meetings CASCADE;
DROP TABLE IF EXISTS access_requests CASCADE;
DROP TABLE IF EXISTS it_tickets CASCADE;
DROP TABLE IF EXISTS employees CASCADE;

-- 1. Create employees table
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    role VARCHAR(100) NOT NULL,
    department VARCHAR(100) DEFAULT 'General',
    password_hash VARCHAR(255),
    date_joined TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create leave_requests table
CREATE TABLE leave_requests (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type VARCHAR(50) NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    reason TEXT DEFAULT '',
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create meetings table
CREATE TABLE meetings (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    organizer_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_minutes INTEGER DEFAULT 30,
    description TEXT DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Create execution_logs table
CREATE TABLE execution_logs (
    id SERIAL PRIMARY KEY,
    request_text TEXT NOT NULL,
    steps_json TEXT NOT NULL,
    result_summary TEXT DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Create access_requests table
CREATE TABLE access_requests (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    system_name VARCHAR(100) NOT NULL,
    access_type VARCHAR(50) DEFAULT 'read',
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Create it_tickets table
CREATE TABLE it_tickets (
    id SERIAL PRIMARY KEY,
    ticket_id VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    category VARCHAR(100) DEFAULT 'General IT',
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'open',
    assigned_team VARCHAR(100) DEFAULT 'General IT Support',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Insert Current Employee Accounts
INSERT INTO employees (name, email, role, department, password_hash) VALUES
    ('Sujay Kathi', 'sujaykathi25csds@rnsit.ac.in', 'CEO & Lead Architect', 'Executive', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9'),
    ('Rahul Kumar', 'rahul@enterprise.com', 'Senior Software Engineer', 'Engineering', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9'),
    ('Roshni', 'br.roshni0031@gmail.com', 'Product Manager', 'Product', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9'),
    ('John Doe', 'john.doe@enterprise.com', 'IT Administrator', 'IT Operations', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9'),
    ('Alice Wang', 'alice.wang@enterprise.com', 'HR Specialist', 'Human Resources', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9'),
    ('Bob Smith', 'bob.smith@enterprise.com', 'DevOps Engineer', 'Engineering', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9');

-- Insert Sample Leave Requests
INSERT INTO leave_requests (employee_id, leave_type, start_date, end_date, reason, status) VALUES
    (1, 'casual', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '2 days', 'Short break', 'approved'),
    (2, 'sick', CURRENT_TIMESTAMP - INTERVAL '1 day', CURRENT_TIMESTAMP, 'Flu', 'approved');

-- Insert Sample IT Tickets
INSERT INTO it_tickets (ticket_id, title, description, priority, status, assigned_team) VALUES
    ('IT-1001', 'VPN Connection Issue', 'Unable to connect to US-East-1 region', 'high', 'open', 'Networking'),
    ('IT-1002', 'New Laptop Request', 'M3 MacBook Pro for new hire', 'medium', 'in_progress', 'Procurement');

-- Insert Sample Meetings
INSERT INTO meetings (title, organizer_id, scheduled_at, duration_minutes, description) VALUES
    ('Project Sync', 2, CURRENT_TIMESTAMP + INTERVAL '2 hours', 60, 'Weekly project update'),
    ('Sprint Planning', 1, CURRENT_TIMESTAMP + INTERVAL '1 day', 90, 'Planning for Q3 Sprint 1');

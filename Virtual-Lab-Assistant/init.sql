
USE Virtual_Lab_Assistant;

-- 1️⃣ Parameter Limits (for check_parameter_limits)
CREATE TABLE parameter_limits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    parameter_name VARCHAR(255) UNIQUE NOT NULL,
    min_value FLOAT,
    max_value FLOAT,
    unit VARCHAR(50)
);

INSERT INTO parameter_limits (parameter_name, min_value, max_value, unit)
VALUES 
    ('membrane_conditioning_temperature', 60, 90, '°C'),
    ('flow_rate', 100, 500, 'mL/min'),
    ('pressure', 5, 30, 'PSI'),
    ('voltage', 0.5, 1.5, 'V'),
    ('current_density', 100, 500, 'mA/cm²'),
    ('temperature', 20, 80, '°C');

-- 2️⃣ Performance Metrics (for check_performance_metrics)
CREATE TABLE performance_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    parameter_name VARCHAR(255) UNIQUE NOT NULL,
    min_value FLOAT,
    max_value FLOAT,
    unit VARCHAR(50)
);

INSERT INTO performance_metrics (parameter_name, min_value, max_value, unit)
VALUES 
    ('voltage_drop', 0.5, 1.5, 'V'),
    ('efficiency', 40, 85, '%'),
    ('power_output', 50, 200, 'W');

-- 3️⃣ Emergency Procedures (for get_emergency_procedure)
CREATE TABLE emergency_procedures (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scenario VARCHAR(255) UNIQUE NOT NULL,
    action TEXT
);

INSERT INTO emergency_procedures (scenario, action)
VALUES 
    ('The hydrogen sensor is beeping', 'Immediately shut off the hydrogen supply and ventilate the room.'),
    ('Smoke is coming from the fuel cell', 'Shut down power and evacuate the area.'),
    ('Fuel leak', 'Shut off the hydrogen supply, evacuate the area, and notify emergency services.'),
    ('Fuel cell overheating', 'Shut down the system, increase ventilation, and monitor temperature.'),
    ('Explosion risk', 'Evacuate immediately and contact emergency services.');

-- 4️⃣ Safety Guidelines (for get_safety_guidelines)
CREATE TABLE lab_safety_guidelines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question VARCHAR(255) UNIQUE NOT NULL,
    response TEXT
);

INSERT INTO lab_safety_guidelines (question, response)
VALUES 
    ('Is it safe to work alone in the fuel cell lab?', 'No, always work with a supervisor.'),
    ('Do I need special gloves for handling the membrane?', 'Yes, use nitrile gloves.'),
    ('What are the safety guidelines?', '1. Wear appropriate PPE (goggles, gloves, lab coat).\n2. Ensure proper ventilation.\n3. Check hydrogen sensors are working.\n4. Know emergency shutdown procedures.\n5. Keep a fire extinguisher nearby.'),
    ('How to store hydrogen safely?', 'Store in a well-ventilated area, away from ignition sources, and use certified containers.'),
    ('What precautions should I take when operating a fuel cell?', 'Ensure proper gas flow, monitor temperature and pressure, and have emergency protocols ready.');

-- LAB AVAILABILITY
CREATE TABLE lab_availability (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lab_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) -- e.g., "available", "occupied"
);

INSERT INTO lab_availability (lab_name, status) VALUES
('PEMFC Research Lab', 'available'),
('SOFC Development Lab', 'occupied');


-- LAB EQUIPMENT
CREATE TABLE lab_equipment (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(255)
);

INSERT INTO lab_equipment (name, location) VALUES
('Microscope', 'Cabinet A, Shelf 2'),
('Beaker', 'Storage Room B, Section 3'),
('Bunsen Burner', 'Lab Station 4'),
('Mass Flow Controller', 'Test Bench 1');

-- EXPERIMENT PROCEDURES
CREATE TABLE experiment_procedures (
    id INT AUTO_INCREMENT PRIMARY KEY,
    experiment_name VARCHAR(100) NOT NULL,
    step TEXT
);

INSERT INTO experiment_procedures (experiment_name, step) VALUES
('Titration', '1. Prepare the burette with NaOH solution'),
('Titration', '2. Add indicator to the acid solution'),
('Titration', '3. Slowly add base while swirling flask'),
('Hydrogen Purge', '1. Connect hydrogen line to purge port'),
('Hydrogen Purge', '2. Open purge valve and monitor pressure');


-- for users    

CREATE TABLE users (
    email VARCHAR(255) PRIMARY KEY,
    password VARCHAR(255) NOT NULL
);

INSERT INTO users (email, password) VALUES
 ('a01@example.com', '123'),
 ('b01@example.com', '123'),
 ('c01@example.com', '123');

-- for user_tokens

CREATE TABLE user_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password VARCHAR(250),
    token TEXT,
    expires_at DATETIME,
    refresh_token TEXT,
    refresh_expires_at DATETIME,
    is_active BOOLEAN DEFAULT TRUE
);

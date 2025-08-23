-- Default Events
INSERT INTO Events (name, first_place_points, second_place_points, third_place_points) VALUES
('Chess', 100, 75, 50),
('Cyquest', 100, 75, 50),
('Dexterity', 100, 75, 50),
('Digital Imaging', 120, 80, 60),
('Fotographia', 100, 75, 50),
('24 Frames', 100, 75, 50),
('Programming', 150, 100, 75),
('Quiz', 100, 75, 50),
('Respawn Console', 80, 60, 40),
('Respawn Mobile', 80, 60, 40),
('Respawn PC', 80, 60, 40),
('Robowars', 120, 80, 60),
('Surprise', 100, 75, 50),
('Verse Off', 100, 75, 50);

-- Default Schools
INSERT INTO Schools (name) VALUES
('Amity International School, Mayur Vihar'),
('Ahlcon Public School, Mayur Vihar'),
('Delhi Public School, R.K. Puram'),
('Delhi Public School, Vasant Kunj'),
('Modern School, Barakhamba Road'),
('Springdales School, Dhaula Kuan'),
('The Shri Ram School, Aravali'),
('Sardar Patel Vidyalaya'),
('Mayoor School, Noida'),
('Somerville School, Noida');

-- Demo Super Admin User
-- Password is 'demo_super_admin'
INSERT INTO Users (username, password_hash, role) VALUES
('demo_super_admin', 'scrypt:32768:8:1$2T5lKTnEdcYQDzXw$4e87879f2ecc7573acc0d60a6c208161217f68498552c87f6cc5c1cf5df027a95297332440923f23d6c3898848a5fb97f07250b004ee1173d2913aa2d3e6e8cc', 'super_admin');

-- Sample Results
INSERT INTO Results (event_id, first_place_school, second_place_school, third_place_school, submitted_at) VALUES
(1, 'Amity International School, Mayur Vihar', 'Delhi Public School, R.K. Puram', 'Modern School, Barakhamba Road', '2025-08-23 09:00:00'),
(2, 'Delhi Public School, Vasant Kunj', 'Ahlcon Public School, Mayur Vihar', 'Springdales School, Dhaula Kuan', '2025-08-23 09:05:00'),
(3, 'The Shri Ram School, Aravali', 'Sardar Patel Vidyalaya', 'Mayoor School, Noida', '2025-08-23 09:10:00');

-- Update results_entered flag for seeded events
UPDATE Events SET results_entered = 1 WHERE id IN (1, 2, 3);

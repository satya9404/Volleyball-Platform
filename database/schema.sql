CREATE DATABASE IF NOT EXISTS volleyball_platform;

USE volleyball_platform;


-- =========================================
-- 1. USERS
-- =========================================

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,

    role ENUM(
        'admin',
        'organizer',
        'user'
    ) NOT NULL DEFAULT 'user',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =========================================
-- 2. TOURNAMENTS
-- =========================================

CREATE TABLE tournaments (
    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(200) NOT NULL,
    description TEXT,

    start_date DATE NOT NULL,
    end_date DATE,

    location VARCHAR(200),

    format ENUM(
        'league',
        'knockout',
        'league_knockout'
    ) NOT NULL,

    status ENUM(
        'draft',
        'pending',
        'approved',
        'ongoing',
        'completed',
        'cancelled'
    ) NOT NULL DEFAULT 'draft',

    created_by INT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (created_by)
        REFERENCES users(id)
        ON DELETE RESTRICT
);


-- =========================================
-- 3. TOURNAMENT ORGANIZERS
-- =========================================

CREATE TABLE tournament_organizers (
    id INT AUTO_INCREMENT PRIMARY KEY,

    tournament_id INT NOT NULL,
    user_id INT NOT NULL,

    organizer_role ENUM(
        'manager',
        'scorer',
        'staff'
    ) NOT NULL DEFAULT 'staff',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (tournament_id)
        REFERENCES tournaments(id)
        ON DELETE CASCADE,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    UNIQUE (tournament_id, user_id)
);


-- =========================================
-- 4. VENUES
-- =========================================

CREATE TABLE venues (
    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(150) NOT NULL,
    location VARCHAR(250),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =========================================
-- 5. TEAMS
-- =========================================

CREATE TABLE teams (
    id INT AUTO_INCREMENT PRIMARY KEY,

    tournament_id INT NOT NULL,

    team_name VARCHAR(150) NOT NULL,
    team_logo VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (tournament_id)
        REFERENCES tournaments(id)
        ON DELETE CASCADE
);


-- =========================================
-- 6. PLAYERS
-- =========================================

CREATE TABLE players (
    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(100) NOT NULL,
    roll_number VARCHAR(50),
    department VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =========================================
-- 7. TEAM PLAYERS
-- =========================================

CREATE TABLE team_players (
    id INT AUTO_INCREMENT PRIMARY KEY,

    team_id INT NOT NULL,
    player_id INT NOT NULL,

    FOREIGN KEY (team_id)
        REFERENCES teams(id)
        ON DELETE CASCADE,

    FOREIGN KEY (player_id)
        REFERENCES players(id)
        ON DELETE CASCADE,

    UNIQUE (team_id, player_id)
);


-- =========================================
-- 8. TOURNAMENT GROUPS
-- =========================================

CREATE TABLE tournament_groups (
    id INT AUTO_INCREMENT PRIMARY KEY,

    tournament_id INT NOT NULL,
    group_name VARCHAR(100) NOT NULL,

    FOREIGN KEY (tournament_id)
        REFERENCES tournaments(id)
        ON DELETE CASCADE,

    UNIQUE (tournament_id, group_name)
);


-- =========================================
-- 9. TOURNAMENT SETTINGS
-- =========================================

CREATE TABLE tournament_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,

    tournament_id INT NOT NULL UNIQUE,

    sets_to_win INT NOT NULL DEFAULT 2,
    points_per_set INT NOT NULL DEFAULT 25,
    final_set_points INT NOT NULL DEFAULT 15,

    FOREIGN KEY (tournament_id)
        REFERENCES tournaments(id)
        ON DELETE CASCADE
);


-- =========================================
-- 10. MATCHES
-- =========================================

CREATE TABLE matches (
    id INT AUTO_INCREMENT PRIMARY KEY,

    tournament_id INT NOT NULL,

    team1_id INT NOT NULL,
    team2_id INT NOT NULL,

    match_date DATE NOT NULL,
    match_time TIME,

    venue_id INT,

    round_name VARCHAR(100),

    status ENUM(
        'scheduled',
        'live',
        'completed',
        'cancelled'
    ) NOT NULL DEFAULT 'scheduled',

    winner_id INT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (tournament_id)
        REFERENCES tournaments(id)
        ON DELETE CASCADE,

    FOREIGN KEY (team1_id)
        REFERENCES teams(id)
        ON DELETE RESTRICT,

    FOREIGN KEY (team2_id)
        REFERENCES teams(id)
        ON DELETE RESTRICT,

    FOREIGN KEY (venue_id)
        REFERENCES venues(id)
        ON DELETE SET NULL,

    FOREIGN KEY (winner_id)
        REFERENCES teams(id)
        ON DELETE SET NULL
);


-- =========================================
-- 11. MATCH SETS
-- =========================================

CREATE TABLE match_sets (
    id INT AUTO_INCREMENT PRIMARY KEY,

    match_id INT NOT NULL,

    set_number INT NOT NULL,

    team1_score INT NOT NULL DEFAULT 0,
    team2_score INT NOT NULL DEFAULT 0,

    winner_id INT NULL,

    FOREIGN KEY (match_id)
        REFERENCES matches(id)
        ON DELETE CASCADE,

    FOREIGN KEY (winner_id)
        REFERENCES teams(id)
        ON DELETE SET NULL,

    UNIQUE (match_id, set_number)
);


-- =========================================
-- 12. ANNOUNCEMENTS
-- =========================================

CREATE TABLE announcements (
    id INT AUTO_INCREMENT PRIMARY KEY,

    tournament_id INT NOT NULL,

    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,

    created_by INT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (tournament_id)
        REFERENCES tournaments(id)
        ON DELETE CASCADE,

    FOREIGN KEY (created_by)
        REFERENCES users(id)
        ON DELETE RESTRICT
);
-- ============================================================
-- NIT NAGALAND VOLLEYBALL TOURNAMENT MANAGEMENT SYSTEM
-- FINAL DATABASE SCHEMA FOR AIVEN MYSQL
--
-- Target database: defaultdb
-- MySQL 8.x
--
-- This schema combines schema(2).sql + schema(3).sql and the
-- database fields currently used by the Volleyball Flask project.
-- ============================================================

USE defaultdb;

-- ------------------------------------------------------------
-- CLEAN START
-- IMPORTANT: These DROP statements delete existing tables/data
-- in defaultdb. Use this file only if this Aiven database is the
-- new/empty database for this project.
-- ------------------------------------------------------------

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS announcements;
DROP TABLE IF EXISTS match_sets;
DROP TABLE IF EXISTS matches;
DROP TABLE IF EXISTS tournament_settings;
DROP TABLE IF EXISTS tournament_groups;
DROP TABLE IF EXISTS team_players;
DROP TABLE IF EXISTS teams;
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS venues;
DROP TABLE IF EXISTS tournament_organizers;
DROP TABLE IF EXISTS tournaments;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;


-- ============================================================
-- 1. USERS
-- ============================================================

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
) ENGINE=InnoDB;


-- ============================================================
-- 2. TOURNAMENTS
-- ============================================================

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

    CONSTRAINT fk_tournaments_created_by
        FOREIGN KEY (created_by)
        REFERENCES users(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB;


-- ============================================================
-- 3. TOURNAMENT ORGANIZERS
-- ============================================================

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

    CONSTRAINT fk_tournament_organizers_tournament
        FOREIGN KEY (tournament_id)
        REFERENCES tournaments(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_tournament_organizers_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    UNIQUE (tournament_id, user_id)
) ENGINE=InnoDB;


-- ============================================================
-- 4. VENUES
-- ============================================================

CREATE TABLE venues (
    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(150) NOT NULL,
    location VARCHAR(250),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;


-- ============================================================
-- 5. PLAYERS
-- ============================================================

CREATE TABLE players (
    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(100) NOT NULL,
    roll_number VARCHAR(50),
    department VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;


-- ============================================================
-- 6. TEAMS
-- ============================================================

CREATE TABLE teams (
    id INT AUTO_INCREMENT PRIMARY KEY,

    tournament_id INT NOT NULL,

    team_name VARCHAR(150) NOT NULL,
    team_logo VARCHAR(255),

    captain_id INT NULL,
    vice_captain_id INT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_teams_tournament
        FOREIGN KEY (tournament_id)
        REFERENCES tournaments(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_teams_captain
        FOREIGN KEY (captain_id)
        REFERENCES players(id)
        ON DELETE SET NULL,

    CONSTRAINT fk_teams_vice_captain
        FOREIGN KEY (vice_captain_id)
        REFERENCES players(id)
        ON DELETE SET NULL,

    UNIQUE (tournament_id, team_name)
) ENGINE=InnoDB;


-- ============================================================
-- 7. TEAM PLAYERS
-- ============================================================

CREATE TABLE team_players (
    id INT AUTO_INCREMENT PRIMARY KEY,

    team_id INT NOT NULL,
    player_id INT NOT NULL,

    CONSTRAINT fk_team_players_team
        FOREIGN KEY (team_id)
        REFERENCES teams(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_team_players_player
        FOREIGN KEY (player_id)
        REFERENCES players(id)
        ON DELETE CASCADE,

    UNIQUE (team_id, player_id)
) ENGINE=InnoDB;


-- ============================================================
-- 8. TOURNAMENT GROUPS
-- ============================================================

CREATE TABLE tournament_groups (
    id INT AUTO_INCREMENT PRIMARY KEY,

    tournament_id INT NOT NULL,
    group_name VARCHAR(100) NOT NULL,

    CONSTRAINT fk_tournament_groups_tournament
        FOREIGN KEY (tournament_id)
        REFERENCES tournaments(id)
        ON DELETE CASCADE,

    UNIQUE (tournament_id, group_name)
) ENGINE=InnoDB;


-- ============================================================
-- 9. TOURNAMENT SETTINGS
-- ============================================================

CREATE TABLE tournament_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,

    tournament_id INT NOT NULL UNIQUE,

    sets_to_win INT NOT NULL DEFAULT 2,
    points_per_set INT NOT NULL DEFAULT 25,
    final_set_points INT NOT NULL DEFAULT 15,

    CONSTRAINT fk_tournament_settings_tournament
        FOREIGN KEY (tournament_id)
        REFERENCES tournaments(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- ============================================================
-- 10. MATCHES
-- ============================================================

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

    CONSTRAINT fk_matches_tournament
        FOREIGN KEY (tournament_id)
        REFERENCES tournaments(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_matches_team1
        FOREIGN KEY (team1_id)
        REFERENCES teams(id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_matches_team2
        FOREIGN KEY (team2_id)
        REFERENCES teams(id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_matches_venue
        FOREIGN KEY (venue_id)
        REFERENCES venues(id)
        ON DELETE SET NULL,

    CONSTRAINT fk_matches_winner
        FOREIGN KEY (winner_id)
        REFERENCES teams(id)
        ON DELETE SET NULL
) ENGINE=InnoDB;


-- ============================================================
-- 11. MATCH SETS / SCORE MANAGEMENT
-- ============================================================

CREATE TABLE match_sets (
    id INT AUTO_INCREMENT PRIMARY KEY,

    match_id INT NOT NULL,

    set_number INT NOT NULL,

    target_points INT NOT NULL DEFAULT 25,

    team1_score INT NOT NULL DEFAULT 0,
    team2_score INT NOT NULL DEFAULT 0,

    winner_id INT NULL,

    CONSTRAINT fk_match_sets_match
        FOREIGN KEY (match_id)
        REFERENCES matches(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_match_sets_winner
        FOREIGN KEY (winner_id)
        REFERENCES teams(id)
        ON DELETE SET NULL,

    UNIQUE (match_id, set_number)
) ENGINE=InnoDB;


-- ============================================================
-- 12. ANNOUNCEMENTS
-- ============================================================

CREATE TABLE announcements (
    id INT AUTO_INCREMENT PRIMARY KEY,

    tournament_id INT NOT NULL,

    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,

    created_by INT NOT NULL,

    attachment_filename VARCHAR(255) NULL,
    attachment_path VARCHAR(500) NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_announcements_tournament
        FOREIGN KEY (tournament_id)
        REFERENCES tournaments(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_announcements_created_by
        FOREIGN KEY (created_by)
        REFERENCES users(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB;


-- ============================================================
-- VERIFY TABLES
-- ============================================================

SHOW TABLES;

-- Expected tables:
-- announcements
-- match_sets
-- matches
-- players
-- teams
-- team_players
-- tournament_groups
-- tournament_organizers
-- tournament_settings
-- tournaments
-- users
-- venues

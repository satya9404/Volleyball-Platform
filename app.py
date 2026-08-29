from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import os
import time

from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(
    app.root_path,
    "static",
    "uploads",
    "announcements"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER



os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "jpg",
    "jpeg",
    "png"
}

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )




app.secret_key = os.getenv("SECRET_KEY")


def get_db_connection():
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=os.getenv("DB_PORT")
    )

    return connection


@app.route("/")
def home():

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )

    try:

        # =====================================================
        # TOTAL TOURNAMENTS
        # =====================================================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM tournaments
        """)

        tournament_count = cursor.fetchone()["total"]


        # =====================================================
        # TOTAL TEAMS
        # =====================================================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM teams
        """)

        team_count = cursor.fetchone()["total"]


        # =====================================================
        # TOTAL PLAYERS
        # =====================================================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM players
        """)

        player_count = cursor.fetchone()["total"]


        # =====================================================
        # TOTAL MATCHES
        # =====================================================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM matches
        """)

        match_count = cursor.fetchone()["total"]


        # =====================================================
        # LIVE MATCH
        # =====================================================

        cursor.execute("""
            SELECT
                m.id,
                m.tournament_id,
                m.team1_id,
                m.team2_id,
                m.match_date,
                m.match_time,
                m.round_name,
                m.status,
                m.winner_id,

                t.name AS tournament_name,

                team1.team_name AS team1_name,
                team2.team_name AS team2_name,

                v.name AS venue_name,
                v.location AS venue_location

            FROM matches m

            JOIN tournaments t
                ON m.tournament_id = t.id

            JOIN teams team1
                ON m.team1_id = team1.id

            JOIN teams team2
                ON m.team2_id = team2.id

            LEFT JOIN venues v
                ON m.venue_id = v.id

            WHERE m.status = 'live'

            ORDER BY
                m.match_date ASC,
                m.match_time ASC

            LIMIT 1
        """)

        live_match = cursor.fetchone()


        # =====================================================
        # UPCOMING MATCHES
        # =====================================================

        cursor.execute("""
            SELECT
                m.id,
                m.tournament_id,
                m.team1_id,
                m.team2_id,
                m.match_date,
                m.match_time,
                m.round_name,
                m.status,

                t.name AS tournament_name,

                team1.team_name AS team1_name,
                team2.team_name AS team2_name,

                v.name AS venue_name,
                v.location AS venue_location

            FROM matches m

            JOIN tournaments t
                ON m.tournament_id = t.id

            JOIN teams team1
                ON m.team1_id = team1.id

            JOIN teams team2
                ON m.team2_id = team2.id

            LEFT JOIN venues v
                ON m.venue_id = v.id

            WHERE m.status = 'scheduled'

            ORDER BY
                m.match_date ASC,
                m.match_time ASC

            LIMIT 4
        """)

        upcoming_matches = cursor.fetchall()


        # =====================================================
        # RECENT RESULTS
        # =====================================================

        cursor.execute("""
            SELECT
                m.id,
                m.tournament_id,
                m.team1_id,
                m.team2_id,
                m.match_date,
                m.match_time,
                m.round_name,
                m.status,
                m.winner_id,

                t.name AS tournament_name,

                team1.team_name AS team1_name,
                team2.team_name AS team2_name

            FROM matches m

            JOIN tournaments t
                ON m.tournament_id = t.id

            JOIN teams team1
                ON m.team1_id = team1.id

            JOIN teams team2
                ON m.team2_id = team2.id

            WHERE m.status = 'completed'

            ORDER BY
                m.match_date DESC,
                m.match_time DESC

            LIMIT 4
        """)

        recent_results = cursor.fetchall()


        # =====================================================
        # ACTIVE / UPCOMING TOURNAMENTS
        # =====================================================

        cursor.execute("""
            SELECT
                id,
                name,
                description,
                start_date,
                end_date,
                location,
                format,
                status

            FROM tournaments

            WHERE status IN (
                'approved',
                'ongoing'
            )

            ORDER BY
                start_date ASC

            LIMIT 4
        """)

        active_tournaments = cursor.fetchall()


        # =====================================================
        # LATEST ANNOUNCEMENTS
        # =====================================================

        cursor.execute("""
            SELECT
                a.id,
                a.tournament_id,
                a.title,
                a.message,
                a.created_at,

                t.name AS tournament_name,

                u.name AS created_by_name

            FROM announcements a

            JOIN tournaments t
                ON a.tournament_id = t.id

            JOIN users u
                ON a.created_by = u.id

            ORDER BY
                a.created_at DESC

            LIMIT 4
        """)

        latest_announcements = cursor.fetchall()


        # =====================================================
        # SEND DATA TO HOME.HTML
        # =====================================================

        return render_template(
            "home.html",

            tournament_count=tournament_count,
            team_count=team_count,
            player_count=player_count,
            match_count=match_count,

            live_match=live_match,
            upcoming_matches=upcoming_matches,
            recent_results=recent_results,

            active_tournaments=active_tournaments,

            latest_announcements=latest_announcements
        )


    finally:

        cursor.close()
        connection.close()

        
@app.route("/api/match/<int:match_id>/score")
def get_live_score(match_id):

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )

    # Get match information
    cursor.execute("""
        SELECT
            m.id,
            m.team1_id,
            m.team2_id,
            m.status,
            m.winner_id,
            t1.team_name AS team1_name,
            t2.team_name AS team2_name
        FROM matches m

        JOIN teams t1
            ON m.team1_id = t1.id

        JOIN teams t2
            ON m.team2_id = t2.id

        WHERE m.id = %s
    """, (match_id,))

    match = cursor.fetchone()

    if not match:
        cursor.close()
        connection.close()

        return {
            "success": False,
            "message": "Match not found"
        }, 404


    # Get latest set scores
    cursor.execute("""
        SELECT
            set_number,
            team1_score,
            team2_score,
            winner_id
        FROM match_sets
        WHERE match_id = %s
        ORDER BY set_number
    """, (match_id,))

    sets = cursor.fetchall()


    # Calculate sets won
    team1_sets = 0
    team2_sets = 0

    for match_set in sets:

        if match_set["winner_id"] == match["team1_id"]:
            team1_sets += 1

        elif match_set["winner_id"] == match["team2_id"]:
            team2_sets += 1


    cursor.close()
    connection.close()


    return {
        "success": True,

        "match_id": match["id"],

        "team1": {
            "id": match["team1_id"],
            "name": match["team1_name"],
            "sets": team1_sets
        },

        "team2": {
            "id": match["team2_id"],
            "name": match["team2_name"],
            "sets": team2_sets
        },

        "status": match["status"],

        "winner_id": match["winner_id"],

        "sets": [
            {
                "set_number": s["set_number"],
                "team1_score": s["team1_score"],
                "team2_score": s["team2_score"],
                "winner_id": s["winner_id"]
            }
            for s in sets
        ]
    }


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            cursor.close()
            connection.close()

            flash("An account with this email already exists.")

            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users
            (name, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            """,
            (name, email, password_hash, "user")
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash("Account created successfully. Please login.")

        return redirect(url_for("login"))

    return render_template("auth/register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, name, email, password_hash, role
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user and check_password_hash(
            user["password_hash"],
            password
        ):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]

            if user["role"] in ("admin", "organizer"):
                return redirect(url_for("organizer_dashboard"))

            return redirect(url_for("home"))

        flash("Invalid email or password.")

    return render_template("auth/login.html")


@app.route("/organizer/dashboard")
def organizer_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") not in ["admin", "organizer"]:
        return redirect(url_for("home"))

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )

    # Total tournaments
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM tournaments
    """)
    result = cursor.fetchone()
    total_tournaments = result["total"] if result else 0

    # Active tournaments
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM tournaments
        WHERE status IN ('approved', 'ongoing')
    """)
    result = cursor.fetchone()
    active_tournaments = result["total"] if result else 0

    # Upcoming matches
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM matches
        WHERE status = 'scheduled'
    """)
    result = cursor.fetchone()
    upcoming_matches = result["total"] if result else 0

    # Live matches
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM matches
        WHERE status = 'live'
    """)
    result = cursor.fetchone()
    live_matches = result["total"] if result else 0

    cursor.close()
    connection.close()

    return render_template(
        "organizer/dashboard.html",
        total_tournaments=total_tournaments,
        active_tournaments=active_tournaments,
        upcoming_matches=upcoming_matches,
        live_matches=live_matches
    )

@app.route("/tournaments")
def tournaments():

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )

    # =========================================
    # GET APPROVED / ONGOING TOURNAMENTS
    # =========================================

    cursor.execute("""
        SELECT
            id,
            name,
            description,
            start_date,
            end_date,
            location,
            format,
            status
        FROM tournaments
        WHERE status IN ('approved', 'ongoing')
        ORDER BY start_date DESC
    """)

    tournaments = cursor.fetchall()

    # =========================================
    # CLOSE DATABASE
    # =========================================

    cursor.close()
    connection.close()

    # =========================================
    # OPEN TOURNAMENTS PAGE
    # =========================================

    return render_template(
        "tournaments.html",
        tournaments=tournaments
    )


@app.route("/tournaments/<int:tournament_id>")
def tournament_details(tournament_id):

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )

    # =========================================
    # GET TOURNAMENT
    # =========================================

    cursor.execute("""
        SELECT
            id,
            name,
            description,
            start_date,
            end_date,
            location,
            format,
            status
        FROM tournaments
        WHERE id = %s
    """, (tournament_id,))

    tournament = cursor.fetchone()

    if not tournament:

        cursor.close()
        connection.close()

        return "Tournament not found", 404


    # =========================================
    # GET TEAMS
    # =========================================

    cursor.execute("""
        SELECT
            id,
            team_name,
            team_logo
        FROM teams
        WHERE tournament_id = %s
        ORDER BY team_name ASC
    """, (tournament_id,))

    teams = cursor.fetchall()


    # =========================================
    # GET MATCHES
    # =========================================

    cursor.execute("""
        SELECT
            m.id,
            m.match_date,
            m.match_time,
            m.round_name,
            m.status,

            team1.team_name AS team1_name,
            team2.team_name AS team2_name,

            v.name AS venue_name

        FROM matches m

        JOIN teams team1
            ON m.team1_id = team1.id

        JOIN teams team2
            ON m.team2_id = team2.id

        LEFT JOIN venues v
            ON m.venue_id = v.id

        WHERE m.tournament_id = %s

        ORDER BY
            m.match_date ASC,
            m.match_time ASC
    """, (tournament_id,))

    matches = cursor.fetchall()


    # =========================================
    # CLOSE DATABASE
    # =========================================

    cursor.close()
    connection.close()


    # =========================================
    # OPEN PAGE
    # =========================================

    return render_template(
        "tournament_details.html",

        tournament=tournament,

        teams=teams,

        matches=matches
    )


@app.route("/organizer/tournament/<int:tournament_id>/team/add",
           methods=["GET", "POST"])
def add_team(tournament_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") not in ["admin", "organizer"]:
        return redirect(url_for("home"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True, buffered=True)

    cursor.execute("""
        SELECT id, name
        FROM tournaments
        WHERE id = %s
    """, (tournament_id,))

    tournament = cursor.fetchone()

    if not tournament:
        cursor.close()
        connection.close()
        return "Tournament not found", 404

    if request.method == "POST":

        team_name = request.form["team_name"].strip()

        if not team_name:
            cursor.close()
            connection.close()
            return "Team name is required", 400

        # Check duplicate team name in this tournament
        cursor.execute("""
            SELECT id
            FROM teams
            WHERE tournament_id = %s
              AND LOWER(team_name) = LOWER(%s)
        """, (tournament_id, team_name))

        existing_team = cursor.fetchone()

        if existing_team:
            cursor.close()
            connection.close()

            return render_template(
                "organizer/add_team.html",
                tournament=tournament,
                error="This team already exists in this tournament."
            )

        # Insert team
        cursor.execute("""
            INSERT INTO teams
            (tournament_id, team_name)
            VALUES (%s, %s)
        """, (tournament_id, team_name))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(
            url_for(
                "tournament_details",
                tournament_id=tournament_id
            )
        )

    cursor.close()
    connection.close()

    return render_template(
        "organizer/add_team.html",
        tournament=tournament
    )

@app.route("/organizer/team/<int:team_id>/player/add", methods=["GET", "POST"])
def add_player(team_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") not in ["admin", "organizer"]:
        return redirect(url_for("home"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True, buffered=True)

    # Get team
    cursor.execute("""
        SELECT
            t.id,
            t.team_name,
            t.tournament_id,
            tr.name AS tournament_name
        FROM teams t
        JOIN tournaments tr
            ON t.tournament_id = tr.id
        WHERE t.id = %s
    """, (team_id,))

    team = cursor.fetchone()

    if not team:
        cursor.close()
        connection.close()
        return "Team not found", 404

    if request.method == "POST":

        name = request.form["name"].strip()
        roll_number = request.form["roll_number"].strip()
        department = request.form["department"].strip()

        if not name:
            cursor.close()
            connection.close()
            return "Player name is required", 400

        # Create player
        cursor.execute("""
            INSERT INTO players
            (name, roll_number, department)
            VALUES (%s, %s, %s)
        """, (
            name,
            roll_number,
            department
        ))

        player_id = cursor.lastrowid

        # Connect player to team
        cursor.execute("""
            INSERT INTO team_players
            (team_id, player_id)
            VALUES (%s, %s)
        """, (
            team_id,
            player_id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(
            url_for(
                "tournament_details",
                tournament_id=team["tournament_id"]
            )
        )

    cursor.close()
    connection.close()

    return render_template(
        "organizer/add_player.html",
        team=team
    )

@app.route("/team/<int:team_id>")
def team_details(team_id):

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )

    # =========================================
    # GET TEAM
    # =========================================

    cursor.execute("""
        SELECT
            t.id,
            t.team_name,
            t.team_logo,
            t.tournament_id,

            t.captain_id,
            t.vice_captain_id,

            tr.name AS tournament_name,

            captain.name AS captain_name,
            vice_captain.name AS vice_captain_name

        FROM teams t

        JOIN tournaments tr
            ON t.tournament_id = tr.id

        LEFT JOIN players captain
            ON t.captain_id = captain.id

        LEFT JOIN players vice_captain
            ON t.vice_captain_id = vice_captain.id

        WHERE t.id = %s
    """, (team_id,))

    team = cursor.fetchone()


    # =========================================
    # CHECK TEAM
    # =========================================

    if not team:

        cursor.close()
        connection.close()

        return "Team not found", 404


    # =========================================
    # GET PLAYERS
    # =========================================

    cursor.execute("""
        SELECT
            p.id,
            p.name,
            p.roll_number,
            p.department

        FROM players p

        JOIN team_players tp
            ON p.id = tp.player_id

        WHERE tp.team_id = %s

        ORDER BY p.name
    """, (team_id,))

    players = cursor.fetchall()


    # =========================================
    # GET TEAM MATCHES
    # =========================================

    cursor.execute("""
        SELECT
            m.id,
            m.match_date,
            m.match_time,
            m.round_name,
            m.status,

            team1.team_name AS team1_name,
            team2.team_name AS team2_name,

            v.name AS venue_name

        FROM matches m

        JOIN teams team1
            ON m.team1_id = team1.id

        JOIN teams team2
            ON m.team2_id = team2.id

        LEFT JOIN venues v
            ON m.venue_id = v.id

        WHERE
            m.team1_id = %s
            OR
            m.team2_id = %s

        ORDER BY
            m.match_date ASC,
            m.match_time ASC
    """, (team_id, team_id))

    matches = cursor.fetchall()


    # =========================================
    # CLOSE DATABASE
    # =========================================

    cursor.close()
    connection.close()


    # =========================================
    # OPEN TEAM DETAILS PAGE
    # =========================================

    return render_template(
        "team_details.html",

        team=team,

        players=players,

        matches=matches
    )





@app.route("/organizer/team/<int:team_id>/manage", methods=["GET", "POST"])
def manage_team(team_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") not in ["admin", "organizer"]:
        return redirect(url_for("home"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True, buffered=True)

    # Get team
    cursor.execute("""
    SELECT
        t.id,
        t.team_name,
        t.team_logo,
        t.tournament_id,
        t.captain_id,
        t.vice_captain_id,
        tr.name AS tournament_name,

        captain.name AS captain_name,
        vice_captain.name AS vice_captain_name

    FROM teams t

    JOIN tournaments tr
        ON t.tournament_id = tr.id

    LEFT JOIN players captain
        ON t.captain_id = captain.id

    LEFT JOIN players vice_captain
        ON t.vice_captain_id = vice_captain.id

    WHERE t.id = %s
""", (team_id,))

    team = cursor.fetchone()

    if not team:
        cursor.close()
        connection.close()
        return "Team not found", 404

    # Get players belonging to this team
    cursor.execute("""
        SELECT
            p.id,
            p.name,
            p.roll_number
        FROM players p
        JOIN team_players tp
            ON p.id = tp.player_id
        WHERE tp.team_id = %s
        ORDER BY p.name
    """, (team_id,))

    players = cursor.fetchall()

    if request.method == "POST":

        captain_id = request.form.get("captain_id") or None
        vice_captain_id = request.form.get("vice_captain_id") or None

        # Captain and vice-captain cannot be the same
        if captain_id and vice_captain_id:
            if captain_id == vice_captain_id:
                cursor.close()
                connection.close()

                return render_template(
                    "organizer/manage_team.html",
                    team=team,
                    players=players,
                    error="Captain and Vice-Captain must be different players."
                )

        # Make sure selected players actually belong to this team
        selected_ids = [
            player["id"]
            for player in players
        ]

        if captain_id and int(captain_id) not in selected_ids:
            cursor.close()
            connection.close()
            return "Invalid captain", 400

        if vice_captain_id and int(vice_captain_id) not in selected_ids:
            cursor.close()
            connection.close()
            return "Invalid vice-captain", 400

        cursor.execute("""
            UPDATE teams
            SET captain_id = %s,
                vice_captain_id = %s
            WHERE id = %s
        """, (
            captain_id,
            vice_captain_id,
            team_id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(
            url_for(
                "team_details",
                team_id=team_id
            )
        )

    cursor.close()
    connection.close()

    return render_template(
        "organizer/manage_team.html",
        team=team,
        players=players
    )

@app.route(
    "/organizer/team/<int:team_id>/player/<int:player_id>/delete",
    methods=["POST"]
)
def delete_player(team_id, player_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") not in ["admin", "organizer"]:
        return redirect(url_for("home"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True, buffered=True)

    # Check whether player belongs to this team
    cursor.execute("""
        SELECT
            p.id,
            p.name,
            t.captain_id,
            t.vice_captain_id
        FROM players p
        JOIN team_players tp
            ON p.id = tp.player_id
        JOIN teams t
            ON tp.team_id = t.id
        WHERE p.id = %s
          AND t.id = %s
    """, (player_id, team_id))

    player = cursor.fetchone()

    if not player:
        cursor.close()
        connection.close()
        return "Player not found in this team", 404

    # Captain cannot be deleted
    if player["captain_id"] == player_id:
        cursor.close()
        connection.close()
        return "Cannot delete Captain. Select another Captain first.", 400

    # Vice-Captain cannot be deleted
    if player["vice_captain_id"] == player_id:
        cursor.close()
        connection.close()
        return "Cannot delete Vice-Captain. Select another Vice-Captain first.", 400

    # Remove player from team
    cursor.execute("""
        DELETE FROM team_players
        WHERE team_id = %s
          AND player_id = %s
    """, (team_id, player_id))

    # Delete player
    cursor.execute("""
        DELETE FROM players
        WHERE id = %s
    """, (player_id,))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(
        url_for(
            "team_details",
            team_id=team_id
        )
    )

@app.route("/matches")
def matches():

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )

    cursor.execute("""
        SELECT
            m.id,
            m.match_date,
            m.match_time,
            m.round_name,
            m.status,
            m.winner_id,

            t.name AS tournament_name,

            team1.team_name AS team1_name,
            team2.team_name AS team2_name,

            v.name AS venue_name,
            v.location AS venue_location

        FROM matches m

        JOIN tournaments t
            ON m.tournament_id = t.id

        JOIN teams team1
            ON m.team1_id = team1.id

        JOIN teams team2
            ON m.team2_id = team2.id

        LEFT JOIN venues v
            ON m.venue_id = v.id

        ORDER BY
            m.match_date,
            m.match_time
    """)

    matches = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "matches.html",
        matches=matches
    )

@app.route(
    "/organizer/match/add",
    methods=["GET", "POST"]
)
def add_match():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") not in ["admin", "organizer"]:
        return redirect(url_for("home"))

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )

    # ==============================
    # GET TOURNAMENTS
    # ==============================

    cursor.execute("""
        SELECT
            id,
            name
        FROM tournaments
        ORDER BY name
    """)

    tournaments = cursor.fetchall()


    # ==============================
    # GET TEAMS
    # ==============================

    cursor.execute("""
        SELECT
            id,
            team_name,
            tournament_id
        FROM teams
        ORDER BY team_name
    """)

    teams = cursor.fetchall()


    # ==============================
    # GET VENUES
    # ==============================

    cursor.execute("""
        SELECT
            id,
            name,
            location
        FROM venues
        ORDER BY name
    """)

    venues = cursor.fetchall()


    # ==============================
    # SAVE MATCH
    # ==============================

    if request.method == "POST":

        tournament_id = request.form.get("tournament_id")
        team1_id = request.form.get("team1_id")
        team2_id = request.form.get("team2_id")
        match_date = request.form.get("match_date")
        match_time = request.form.get("match_time") or None
        round_name = request.form.get("round_name") or None
        venue_id = request.form.get("venue_id") or None
        status = request.form.get("status") or "scheduled"


        if not tournament_id:
            return render_template(
                "organizer/add_match.html",
                tournaments=tournaments,
                teams=teams,
                venues=venues,
                error="Please select a tournament."
            )


        if not team1_id or not team2_id:

            return render_template(
                "organizer/add_match.html",
                tournaments=tournaments,
                teams=teams,
                venues=venues,
                error="Please select both teams."
            )


        if team1_id == team2_id:

            return render_template(
                "organizer/add_match.html",
                tournaments=tournaments,
                teams=teams,
                venues=venues,
                error="Team 1 and Team 2 cannot be the same."
            )


        if not match_date:

            return render_template(
                "organizer/add_match.html",
                tournaments=tournaments,
                teams=teams,
                venues=venues,
                error="Match date is required."
            )


        # ==============================
        # INSERT MATCH
        # ==============================

        cursor.execute("""
            INSERT INTO matches
            (
                tournament_id,
                team1_id,
                team2_id,
                match_date,
                match_time,
                round_name,
                venue_id,
                status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """, (
            tournament_id,
            team1_id,
            team2_id,
            match_date,
            match_time,
            round_name,
            venue_id,
            status
        ))


        connection.commit()

        cursor.close()
        connection.close()

        return redirect(
            url_for("matches")
        )


    cursor.close()
    connection.close()


    return render_template(
        "organizer/add_match.html",
        tournaments=tournaments,
        teams=teams,
        venues=venues
    )


@app.route("/admin/tournaments")
def admin_tournaments():

    # Only admin can access this page
    if session.get("user_role") != "admin":
        return "Access denied", 403

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )

    cursor.execute("""
        SELECT
            id,
            name,
            status
        FROM tournaments
        ORDER BY id
    """)

    tournaments = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "organizer/admin_tournaments.html",
        tournaments=tournaments
    )

@app.route(
    "/admin/tournaments/<int:tournament_id>/approve",
    methods=["POST"]
)
def approve_tournament(tournament_id):

    # Only admin can approve
    if session.get("user_role") != "admin":
        return "Access denied", 403

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )

    cursor.execute("""
        UPDATE tournaments
        SET status = 'approved'
        WHERE id = %s
    """, (tournament_id,))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("admin_tournaments"))



@app.route(
    "/organizer/match/<int:match_id>/edit",
    methods=["GET", "POST"]
)
def edit_match(match_id):

    # =====================================================
    # LOGIN CHECK
    # =====================================================

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") not in ["admin", "organizer"]:
        return redirect(url_for("home"))


    # =====================================================
    # DATABASE CONNECTION
    # =====================================================

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )


    # =====================================================
    # GET EXISTING MATCH
    # =====================================================

    cursor.execute("""
        SELECT
            id,
            tournament_id,
            team1_id,
            team2_id,
            match_date,
            match_time,
            venue_id,
            round_name,
            status
        FROM matches
        WHERE id = %s
    """, (match_id,))

    match = cursor.fetchone()


    # =====================================================
    # MATCH NOT FOUND
    # =====================================================

    if not match:

        cursor.close()
        connection.close()

        return "Match not found", 404


    # =====================================================
    # GET TOURNAMENTS
    # =====================================================

    cursor.execute("""
        SELECT
            id,
            name
        FROM tournaments
        ORDER BY name
    """)

    tournaments = cursor.fetchall()


    # =====================================================
    # GET TEAMS
    # =====================================================

    cursor.execute("""
        SELECT
            id,
            team_name,
            tournament_id
        FROM teams
        ORDER BY team_name
    """)

    teams = cursor.fetchall()


    # =====================================================
    # GET VENUES
    # =====================================================

    cursor.execute("""
        SELECT
            id,
            name,
            location
        FROM venues
        ORDER BY name
    """)

    venues = cursor.fetchall()


    # =====================================================
    # UPDATE MATCH
    # =====================================================

    if request.method == "POST":

        tournament_id = request.form.get(
            "tournament_id"
        )

        team1_id = request.form.get(
            "team1_id"
        )

        team2_id = request.form.get(
            "team2_id"
        )

        match_date = request.form.get(
            "match_date"
        )

        match_time = request.form.get(
            "match_time"
        ) or None

        venue_id = request.form.get(
            "venue_id"
        ) or None

        round_name = request.form.get(
            "round_name"
        ) or None

        status = request.form.get(
            "status"
        ) or "scheduled"


        # =================================================
        # VALIDATION
        # =================================================

        if not tournament_id:

            cursor.close()
            connection.close()

            return render_template(
                "organizer/edit_match.html",
                match=match,
                tournaments=tournaments,
                teams=teams,
                venues=venues,
                error="Please select a tournament."
            )


        if not team1_id or not team2_id:

            cursor.close()
            connection.close()

            return render_template(
                "organizer/edit_match.html",
                match=match,
                tournaments=tournaments,
                teams=teams,
                venues=venues,
                error="Please select both teams."
            )


        if team1_id == team2_id:

            cursor.close()
            connection.close()

            return render_template(
                "organizer/edit_match.html",
                match=match,
                tournaments=tournaments,
                teams=teams,
                venues=venues,
                error="Team 1 and Team 2 must be different."
            )


        if not match_date:

            cursor.close()
            connection.close()

            return render_template(
                "organizer/edit_match.html",
                match=match,
                tournaments=tournaments,
                teams=teams,
                venues=venues,
                error="Match date is required."
            )


        # =================================================
        # CHECK TEAM 1 BELONGS TO SELECTED TOURNAMENT
        # =================================================

        cursor.execute("""
            SELECT id
            FROM teams
            WHERE id = %s
              AND tournament_id = %s
        """, (
            team1_id,
            tournament_id
        ))

        valid_team1 = cursor.fetchone()


        if not valid_team1:

            cursor.close()
            connection.close()

            return render_template(
                "organizer/edit_match.html",
                match=match,
                tournaments=tournaments,
                teams=teams,
                venues=venues,
                error="Team 1 does not belong to the selected tournament."
            )


        # =================================================
        # CHECK TEAM 2 BELONGS TO SELECTED TOURNAMENT
        # =================================================

        cursor.execute("""
            SELECT id
            FROM teams
            WHERE id = %s
              AND tournament_id = %s
        """, (
            team2_id,
            tournament_id
        ))

        valid_team2 = cursor.fetchone()


        if not valid_team2:

            cursor.close()
            connection.close()

            return render_template(
                "organizer/edit_match.html",
                match=match,
                tournaments=tournaments,
                teams=teams,
                venues=venues,
                error="Team 2 does not belong to the selected tournament."
            )


        # =================================================
        # UPDATE MATCH
        # =================================================

        cursor.execute("""
            UPDATE matches
            SET
                tournament_id = %s,
                team1_id = %s,
                team2_id = %s,
                match_date = %s,
                match_time = %s,
                venue_id = %s,
                round_name = %s,
                status = %s
            WHERE id = %s
        """, (
            tournament_id,
            team1_id,
            team2_id,
            match_date,
            match_time,
            venue_id,
            round_name,
            status,
            match_id
        ))


        # =================================================
        # SAVE CHANGES
        # =================================================

        connection.commit()


        # =================================================
        # CLOSE DATABASE
        # =================================================

        cursor.close()
        connection.close()


        # =================================================
        # RETURN TO MATCHES
        # =================================================

        return redirect(
            url_for("matches")
        )


    # =====================================================
    # GET REQUEST
    # =====================================================

    cursor.close()
    connection.close()


    return render_template(
        "organizer/edit_match.html",
        match=match,
        tournaments=tournaments,
        teams=teams,
        venues=venues
    )


@app.route(
    "/organizer/match/<int:match_id>/delete",
    methods=["POST"]
)
def delete_match(match_id):

    # =====================================================
    # LOGIN CHECK
    # =====================================================

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") not in ["admin", "organizer"]:
        return redirect(url_for("home"))


    # =====================================================
    # DATABASE CONNECTION
    # =====================================================

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )


    try:

        # =================================================
        # CHECK WHETHER MATCH EXISTS
        # =================================================

        cursor.execute("""
            SELECT id
            FROM matches
            WHERE id = %s
        """, (match_id,))

        match = cursor.fetchone()


        if not match:

            return "Match not found", 404


        # =================================================
        # DELETE MATCH SCORES FIRST
        # =================================================

        cursor.execute("""
            DELETE FROM match_sets
            WHERE match_id = %s
        """, (match_id,))


        # =================================================
        # DELETE MATCH
        # =================================================

        cursor.execute("""
            DELETE FROM matches
            WHERE id = %s
        """, (match_id,))


        # =================================================
        # SAVE
        # =================================================

        connection.commit()


    except Exception as e:

        connection.rollback()

        return f"Error deleting match: {e}", 500


    finally:

        cursor.close()
        connection.close()


    # =====================================================
    # RETURN TO MATCHES
    # =====================================================

    return redirect(
        url_for("matches")
    )



@app.route("/matches/<int:match_id>")
def match_details(match_id):

    # ==========================================
    # DATABASE CONNECTION
    # ==========================================

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )


    # ==========================================
    # GET MATCH DETAILS
    # ==========================================

    cursor.execute("""
        SELECT
            m.id,
            m.tournament_id,
            m.match_date,
            m.match_time,
            m.round_name,
            m.status,
            m.winner_id,

            t.name AS tournament_name,

            team1.id AS team1_id,
            team1.team_name AS team1_name,

            team2.id AS team2_id,
            team2.team_name AS team2_name,

            v.name AS venue_name,
            v.location AS venue_location

        FROM matches m

        JOIN tournaments t
            ON m.tournament_id = t.id

        JOIN teams team1
            ON m.team1_id = team1.id

        JOIN teams team2
            ON m.team2_id = team2.id

        LEFT JOIN venues v
            ON m.venue_id = v.id

        WHERE m.id = %s
    """, (match_id,))

    match = cursor.fetchone()


    # ==========================================
    # CHECK MATCH
    # ==========================================

    if not match:

        cursor.close()
        connection.close()

        return "Match not found", 404


    # ==========================================
    # GET SET SCORES
    # ==========================================

    cursor.execute("""
        SELECT
            id,
            set_number,
            team1_score,
            team2_score,
            winner_id

        FROM match_sets

        WHERE match_id = %s

        ORDER BY set_number ASC
    """, (match_id,))

    sets = cursor.fetchall()


    # ==========================================
    # CALCULATE SETS WON
    # ==========================================

    team1_sets = 0
    team2_sets = 0

    for match_set in sets:

        if match_set["winner_id"] == match["team1_id"]:

            team1_sets += 1

        elif match_set["winner_id"] == match["team2_id"]:

            team2_sets += 1


    # ==========================================
    # CLOSE DATABASE
    # ==========================================

    cursor.close()
    connection.close()


    # ==========================================
    # DISPLAY MATCH DETAILS
    # ==========================================

    return render_template(
        "match_details.html",

        match=match,

        sets=sets,

        team1_sets=team1_sets,

        team2_sets=team2_sets
    )

@app.route("/results")
def results():

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )

    # =====================================================
    # GET COMPLETED MATCHES
    # =====================================================

    cursor.execute("""
        SELECT
            m.id,
            m.match_date,
            m.match_time,
            m.round_name,
            m.status,
            m.winner_id,

            tr.name AS tournament_name,

            team1.team_name AS team1_name,
            team2.team_name AS team2_name,

            v.name AS venue_name,
            v.location AS venue_location

        FROM matches m

        JOIN tournaments tr
            ON m.tournament_id = tr.id

        JOIN teams team1
            ON m.team1_id = team1.id

        JOIN teams team2
            ON m.team2_id = team2.id

        LEFT JOIN venues v
            ON m.venue_id = v.id

        WHERE m.status = 'completed'

        ORDER BY
            m.match_date DESC,
            m.match_time DESC
    """)

    results = cursor.fetchall()

    # =====================================================
    # GET SET SCORES FOR EACH MATCH
    # =====================================================

    for result in results:

        cursor.execute("""
            SELECT
                set_number,
                team1_score,
                team2_score,
                winner_id

            FROM match_sets

            WHERE match_id = %s

            ORDER BY set_number
        """, (result["id"],))

        result["sets"] = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "results.html",
        results=results
    )



@app.route("/announcements")
def announcements():

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )

    # ==========================================
    # GET ANNOUNCEMENTS
    # ==========================================

    cursor.execute("""
        SELECT
            a.id,
            a.title,
            a.message,
            a.created_at,

            -- ATTACHMENT
            a.attachment_filename,
            a.attachment_path,

            t.id AS tournament_id,
            t.name AS tournament_name,

            u.name AS created_by_name

        FROM announcements a

        JOIN tournaments t
            ON a.tournament_id = t.id

        JOIN users u
            ON a.created_by = u.id

        ORDER BY a.created_at DESC
    """)

    announcements = cursor.fetchall()

    # ==========================================
    # CLOSE DATABASE
    # ==========================================

    cursor.close()
    connection.close()

    # ==========================================
    # OPEN ANNOUNCEMENTS PAGE
    # ==========================================

    return render_template(
        "announcements.html",
        announcements=announcements
    )




@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))

@app.route("/organizer/tournament/create", methods=["GET", "POST"])
def create_tournament():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") not in ["admin", "organizer"]:
        return redirect(url_for("home"))

    if request.method == "POST":

        name = request.form["name"]
        description = request.form["description"]
        start_date = request.form["start_date"]
        end_date = request.form.get("end_date") or None
        location = request.form["location"]
        tournament_format = request.form["format"]

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO tournaments
            (
                name,
                description,
                start_date,
                end_date,
                location,
                format,
                status,
                created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            name,
            description,
            start_date,
            end_date,
            location,
            tournament_format,
            "draft",
            session["user_id"]
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("tournaments"))

    return render_template("organizer/create_tournament.html")


@app.route(
    "/organizer/tournament/<int:tournament_id>/teams"
)
def manage_teams(tournament_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") not in ["admin", "organizer"]:
        return redirect(url_for("home"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True, buffered=True)

    # Get tournament
    cursor.execute("""
        SELECT
            id,
            name,
            description,
            start_date,
            end_date,
            location,
            format,
            status
        FROM tournaments
        WHERE id = %s
    """, (tournament_id,))

    tournament = cursor.fetchone()

    if not tournament:
        cursor.close()
        connection.close()

        return "Tournament not found", 404

    # Get teams
    cursor.execute("""
        SELECT
            id,
            team_name,
            team_logo
        FROM teams
        WHERE tournament_id = %s
        ORDER BY team_name
    """, (tournament_id,))

    teams = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "organizer/manage_teams.html",
        tournament=tournament,
        teams=teams
    )


# ==========================================
# UPDATE MATCH SCORE
# ==========================================
# ==========================================
# UPDATE MATCH SCORE
# ==========================================

@app.route("/matches/<int:match_id>/score", methods=["GET", "POST"])
def update_score(match_id):

    if session.get("user_role") not in ["admin", "organizer"]:
            return {
                "success": False,
                "message": "You are not authorized to update the score."
            }, 403


    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True, buffered=True)

    # ==========================================
    # GET MATCH INFORMATION
    # ==========================================

    cursor.execute("""
        SELECT
            m.id,
            m.team1_id,
            m.team2_id,

            team1.team_name AS team1_name,
            team2.team_name AS team2_name

        FROM matches m

        JOIN teams team1
            ON m.team1_id = team1.id

        JOIN teams team2
            ON m.team2_id = team2.id

        WHERE m.id = %s
    """, (match_id,))

    match = cursor.fetchone()


    # ==========================================
    # MATCH NOT FOUND
    # ==========================================

    if not match:

        cursor.close()
        connection.close()

        return "Match not found", 404


    # ==========================================
    # GET EXISTING SET SCORES
    # ==========================================

    cursor.execute("""
        SELECT
            id,
            match_id,
            set_number,
            team1_score,
            team2_score,
            winner_id

        FROM match_sets

        WHERE match_id = %s

        ORDER BY set_number
    """, (match_id,))

    sets = cursor.fetchall()


    # ==========================================
    # SAVE SCORE
    # ==========================================

    if request.method == "POST":

        for set_number in range(1, 6):

            team1_score = request.form.get(
                f"team1_score_{set_number}"
            )

            team2_score = request.form.get(
                f"team2_score_{set_number}"
            )


            # --------------------------------------
            # SKIP EMPTY SET
            # --------------------------------------

            if (
                team1_score is None
                or team2_score is None
                or team1_score == ""
                or team2_score == ""
            ):
                continue


            # --------------------------------------
            # CONVERT SCORE TO INTEGER
            # --------------------------------------

            try:

                team1_score = int(team1_score)
                team2_score = int(team2_score)

            except ValueError:

                cursor.close()
                connection.close()

                return "Invalid score", 400


            # --------------------------------------
            # VALIDATE SCORE
            # --------------------------------------

            if team1_score < 0 or team2_score < 0:

                cursor.close()
                connection.close()

                return "Score cannot be negative", 400


            # --------------------------------------
            # DETERMINE SET WINNER
            # --------------------------------------

            if team1_score > team2_score:

                winner_id = match["team1_id"]

            elif team2_score > team1_score:

                winner_id = match["team2_id"]

            else:

                winner_id = None


            # ======================================
            # CHECK WHETHER SET ALREADY EXISTS
            # ======================================

            cursor.execute("""
                SELECT id

                FROM match_sets

                WHERE match_id = %s
                AND set_number = %s
            """, (
                match_id,
                set_number
            ))

            existing_set = cursor.fetchone()


            # ======================================
            # UPDATE EXISTING SET
            # ======================================

            if existing_set:

                cursor.execute("""
                    UPDATE match_sets

                    SET
                        team1_score = %s,
                        team2_score = %s,
                        winner_id = %s

                    WHERE match_id = %s
                    AND set_number = %s
                """, (
                    team1_score,
                    team2_score,
                    winner_id,
                    match_id,
                    set_number
                ))


            # ======================================
            # INSERT NEW SET
            # ======================================

            else:

                cursor.execute("""
                    INSERT INTO match_sets
                    (
                        match_id,
                        set_number,
                        team1_score,
                        team2_score,
                        winner_id
                    )

                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                """, (
                    match_id,
                    set_number,
                    team1_score,
                    team2_score,
                    winner_id
                ))


        # ==========================================
        # DETERMINE MATCH WINNER
        # ==========================================

        cursor.execute("""
            SELECT
                winner_id,
                COUNT(*) AS set_wins

            FROM match_sets

            WHERE match_id = %s
            AND winner_id IS NOT NULL

            GROUP BY winner_id

            ORDER BY set_wins DESC
        """, (match_id,))

        winner_data = cursor.fetchall()


        # ==========================================
        # UPDATE MATCH RESULT
        # ==========================================

        if winner_data and winner_data[0]["set_wins"] >= 2:

            match_winner_id = winner_data[0]["winner_id"]

            cursor.execute("""
                UPDATE matches

                SET
                    winner_id = %s,
                    status = 'completed'

                WHERE id = %s
            """, (
                match_winner_id,
                match_id
            ))


        # ==========================================
        # SAVE ALL CHANGES
        # ==========================================

        connection.commit()


        # ==========================================
        # CLOSE DATABASE
        # ==========================================

        cursor.close()
        connection.close()


        # ==========================================
        # RETURN TO MATCH DETAILS
        # ==========================================

        return redirect(
            url_for(
                "match_details",
                match_id=match_id
            )
        )


    # ==========================================
    # OPEN UPDATE SCORE PAGE
    # ==========================================

    cursor.close()
    connection.close()

    return render_template(
        "update_score.html",
        match=match,
        sets=sets
    )


@app.route("/api/tournaments/<int:tournament_id>/teams")
def get_tournament_teams(tournament_id):

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )

    cursor.execute("""
        SELECT
            id,
            team_name
        FROM teams
        WHERE tournament_id = %s
        ORDER BY team_name
    """, (tournament_id,))

    teams = cursor.fetchall()

    cursor.close()
    connection.close()

    return teams

@app.route("/team/<int:team_id>/add-player", methods=["GET", "POST"])
def add_team_player(team_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") not in ["admin", "organizer"]:
        return redirect(url_for("home"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True, buffered=True)

    # =========================================
    # GET TEAM
    # =========================================

    cursor.execute("""
        SELECT
            id,
            team_name,
            tournament_id
        FROM teams
        WHERE id = %s
    """, (team_id,))

    team = cursor.fetchone()

    if not team:
        cursor.close()
        connection.close()
        return "Team not found", 404


    # =========================================
    # ADD PLAYER
    # =========================================

    if request.method == "POST":

        player_id = request.form.get("player_id")

        if not player_id:
            cursor.close()
            connection.close()
            return "Please select a player", 400

        # Check if player already belongs to this team
        cursor.execute("""
            SELECT id
            FROM team_players
            WHERE team_id = %s
              AND player_id = %s
        """, (team_id, player_id))

        existing = cursor.fetchone()

        if existing:
            cursor.close()
            connection.close()
            return "Player is already a member of this team"

        # Add player
        cursor.execute("""
            INSERT INTO team_players
            (
                team_id,
                player_id
            )
            VALUES (%s, %s)
        """, (team_id, player_id))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(
            url_for("team_details", team_id=team_id)
        )


    # =========================================
    # GET ALL PLAYERS
    # =========================================

    cursor.execute("""
        SELECT
            id,
            name,
            roll_number,
            department
        FROM players
        ORDER BY name ASC
    """)

    players = cursor.fetchall()


    # =========================================
    # CLOSE DATABASE
    # =========================================

    cursor.close()
    connection.close()


    return render_template(
        "organizer/add_team_player.html",
        team=team,
        players=players
    )

@app.route("/organizer/team/<int:team_id>/captains", methods=["GET", "POST"])
def assign_captains(team_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") not in ["admin", "organizer"]:
        return redirect(url_for("home"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True, buffered=True)

    # Get team
    cursor.execute("""
        SELECT
            t.id,
            t.team_name,
            t.tournament_id,
            t.captain_id,
            t.vice_captain_id
        FROM teams t
        WHERE t.id = %s
    """, (team_id,))

    team = cursor.fetchone()

    if not team:
        cursor.close()
        connection.close()
        return "Team not found", 404

    # Get players belonging to this team
    cursor.execute("""
        SELECT
            p.id,
            p.name,
            p.roll_number,
            p.department
        FROM players p
        JOIN team_players tp
            ON p.id = tp.player_id
        WHERE tp.team_id = %s
        ORDER BY p.name
    """, (team_id,))

    players = cursor.fetchall()

    if request.method == "POST":

        captain_id = request.form.get("captain_id")
        vice_captain_id = request.form.get("vice_captain_id")

        # Both must be selected
        if not captain_id or not vice_captain_id:
            cursor.close()
            connection.close()

            return render_template(
                "organizer/assign_captains.html",
                team=team,
                players=players,
                error="Please select both Captain and Vice Captain."
            )

        # Captain and Vice Captain cannot be the same
        if captain_id == vice_captain_id:
            cursor.close()
            connection.close()

            return render_template(
                "organizer/assign_captains.html",
                team=team,
                players=players,
                error="Captain and Vice Captain must be different players."
            )

        # Update team
        cursor.execute("""
            UPDATE teams
            SET
                captain_id = %s,
                vice_captain_id = %s
            WHERE id = %s
        """, (
            captain_id,
            vice_captain_id,
            team_id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(
            url_for(
                "team_details",
                team_id=team_id
            )
        )

    cursor.close()
    connection.close()

    return render_template(
        "organizer/assign_captains.html",
        team=team,
        players=players
    )

@app.route("/team/<int:team_id>/add-new-player", methods=["GET", "POST"])
def add_new_player(team_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") not in ["admin", "organizer"]:
        return redirect(url_for("home"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True, buffered=True)

    # Get team information
    cursor.execute("""
        SELECT
            t.id,
            t.team_name,
            t.tournament_id,
            tr.name AS tournament_name
        FROM teams t
        JOIN tournaments tr
            ON t.tournament_id = tr.id
        WHERE t.id = %s
    """, (team_id,))

    team = cursor.fetchone()

    if not team:
        cursor.close()
        connection.close()
        return "Team not found", 404

    # -----------------------------
    # ADD NEW PLAYER
    # -----------------------------
    if request.method == "POST":

        name = request.form.get("name", "").strip()
        roll_number = request.form.get("roll_number", "").strip()
        department = request.form.get("department", "").strip()

        if not name:
            cursor.close()
            connection.close()

            return render_template(
                "organizer/add_new_player.html",
                team=team,
                error="Player name is required."
            )

        # Check whether same player already exists
        cursor.execute("""
            SELECT id
            FROM players
            WHERE roll_number = %s
        """, (roll_number,))

        existing_player = cursor.fetchone()

        if existing_player:

            player_id = existing_player["id"]

        else:

            # Create new player
            cursor.execute("""
                INSERT INTO players
                (name, roll_number, department)
                VALUES (%s, %s, %s)
            """, (
                name,
                roll_number if roll_number else None,
                department if department else None
            ))

            player_id = cursor.lastrowid

        # Check if player is already in this team
        cursor.execute("""
            SELECT id
            FROM team_players
            WHERE team_id = %s
              AND player_id = %s
        """, (team_id, player_id))

        already_added = cursor.fetchone()

        if already_added:

            connection.rollback()
            cursor.close()
            connection.close()

            return render_template(
                "organizer/add_new_player.html",
                team=team,
                error="This player is already a member of this team."
            )

        # Add player to team
        cursor.execute("""
            INSERT INTO team_players
            (team_id, player_id)
            VALUES (%s, %s)
        """, (team_id, player_id))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(
            url_for(
                "team_details",
                team_id=team_id
            )
        )

    cursor.close()
    connection.close()

    return render_template(
        "organizer/add_new_player.html",
        team=team
    )

@app.route(
    "/organizer/match/<int:match_id>/score/add",
    methods=["GET", "POST"]
)
def add_match_score(match_id):

    # =====================================================
    # LOGIN CHECK
    # =====================================================

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") not in ["admin", "organizer"]:
        return redirect(url_for("home"))


    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )


    # =====================================================
    # GET MATCH
    # =====================================================

    cursor.execute("""
        SELECT
            m.id,
            m.tournament_id,
            m.team1_id,
            m.team2_id,
            m.status,
            m.winner_id,

            team1.team_name AS team1_name,
            team2.team_name AS team2_name

        FROM matches m

        JOIN teams team1
            ON m.team1_id = team1.id

        JOIN teams team2
            ON m.team2_id = team2.id

        WHERE m.id = %s
    """, (match_id,))

    match = cursor.fetchone()


    if not match:

        cursor.close()
        connection.close()

        return "Match not found", 404


    # =====================================================
    # GET EXISTING SETS
    # =====================================================

    cursor.execute("""
        SELECT
            id,
            set_number,
            team1_score,
            team2_score,
            winner_id

        FROM match_sets

        WHERE match_id = %s

        ORDER BY set_number
    """, (match_id,))

    sets = cursor.fetchall()


    # =====================================================
    # CALCULATE CURRENT SET WINS
    # =====================================================

    team1_sets = 0
    team2_sets = 0

    for match_set in sets:

        if match_set["winner_id"] == match["team1_id"]:
            team1_sets += 1

        elif match_set["winner_id"] == match["team2_id"]:
            team2_sets += 1


    # =====================================================
    # SAVE NEW SET
    # =====================================================

    if request.method == "POST":

        set_number = request.form.get("set_number")
        team1_score = request.form.get("team1_score")
        team2_score = request.form.get("team2_score")


        # =================================================
        # CONVERT TO INTEGER
        # =================================================

        try:

            set_number = int(set_number)
            team1_score = int(team1_score)
            team2_score = int(team2_score)

        except (TypeError, ValueError):

            cursor.close()
            connection.close()

            return render_template(
                "organizer/add_match_score.html",
                match=match,
                sets=sets,
                team1_sets=team1_sets,
                team2_sets=team2_sets,
                error="Please enter valid scores."
            )


        # =================================================
        # SET NUMBER VALIDATION
        # =================================================

        if set_number < 1 or set_number > 3:

            cursor.close()
            connection.close()

            return render_template(
                "organizer/add_match_score.html",
                match=match,
                sets=sets,
                team1_sets=team1_sets,
                team2_sets=team2_sets,
                error="Only Set 1, Set 2 and Set 3 are allowed."
            )


        # =================================================
        # SCORE VALIDATION
        # =================================================

        if team1_score < 0 or team2_score < 0:

            cursor.close()
            connection.close()

            return render_template(
                "organizer/add_match_score.html",
                match=match,
                sets=sets,
                team1_sets=team1_sets,
                team2_sets=team2_sets,
                error="Scores cannot be negative."
            )


        if team1_score == team2_score:

            cursor.close()
            connection.close()

            return render_template(
                "organizer/add_match_score.html",
                match=match,
                sets=sets,
                team1_sets=team1_sets,
                team2_sets=team2_sets,
                error="A set cannot end with equal scores."
            )


        # =================================================
        # DETERMINE SET WINNER
        # =================================================

        if team1_score > team2_score:

            set_winner_id = match["team1_id"]

        else:

            set_winner_id = match["team2_id"]


        # =================================================
        # CHECK IF SET ALREADY EXISTS
        # =================================================

        cursor.execute("""
            SELECT
                id
            FROM match_sets
            WHERE match_id = %s
              AND set_number = %s
        """, (
            match_id,
            set_number
        ))

        existing_set = cursor.fetchone()


        # =================================================
        # UPDATE EXISTING SET
        # =================================================

        if existing_set:

            cursor.execute("""
                UPDATE match_sets

                SET
                    team1_score = %s,
                    team2_score = %s,
                    winner_id = %s

                WHERE id = %s
            """, (
                team1_score,
                team2_score,
                set_winner_id,
                existing_set["id"]
            ))


        # =================================================
        # INSERT NEW SET
        # =================================================

        else:

            cursor.execute("""
                INSERT INTO match_sets
                (
                    match_id,
                    set_number,
                    team1_score,
                    team2_score,
                    winner_id
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """, (
                match_id,
                set_number,
                team1_score,
                team2_score,
                set_winner_id
            ))


        connection.commit()


        # =================================================
        # RECALCULATE SET WINS
        # =================================================

        cursor.execute("""
            SELECT
                winner_id,
                COUNT(*) AS wins

            FROM match_sets

            WHERE match_id = %s
              AND winner_id IS NOT NULL

            GROUP BY winner_id
        """, (match_id,))

        results = cursor.fetchall()


        match_winner_id = None

        for result in results:

            if result["wins"] >= 2:

                match_winner_id = result["winner_id"]

                break


        # =================================================
        # MATCH COMPLETED
        # =================================================

        if match_winner_id:

            cursor.execute("""
                UPDATE matches

                SET
                    winner_id = %s,
                    status = 'completed'

                WHERE id = %s
            """, (
                match_winner_id,
                match_id
            ))

            connection.commit()


        # =================================================
        # CLOSE DATABASE
        # =================================================

        cursor.close()
        connection.close()


        # =================================================
        # RETURN TO MATCH DETAILS
        # =================================================

        return redirect(
            url_for(
                "match_details",
                match_id=match_id
            )
        )


    # =====================================================
    # DISPLAY SCORE MANAGEMENT
    # =====================================================

    cursor.close()
    connection.close()


    return render_template(
        "organizer/add_match_score.html",
        match=match,
        sets=sets,
        team1_sets=team1_sets,
        team2_sets=team2_sets
    )


@app.route("/organizer/match/<int:match_id>/score")
def score_management(match_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") not in ["admin", "organizer"]:
        return redirect(url_for("home"))

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )

    cursor.execute("""
        SELECT
            m.id,
            m.tournament_id,
            m.team1_id,
            m.team2_id,
            m.match_date,
            m.match_time,
            m.venue_id,
            m.round_name,
            m.status,
            m.winner_id,

            t1.team_name AS team1_name,
            t2.team_name AS team2_name,

            v.name AS venue_name,
            v.location AS venue_location,

            tr.name AS tournament_name

        FROM matches m

        JOIN teams t1
            ON m.team1_id = t1.id

        JOIN teams t2
            ON m.team2_id = t2.id

        LEFT JOIN venues v
            ON m.venue_id = v.id

        JOIN tournaments tr
            ON m.tournament_id = tr.id

        WHERE m.id = %s
    """, (match_id,))

    match = cursor.fetchone()

    if not match:
        cursor.close()
        connection.close()
        return "Match not found", 404


    cursor.execute("""
        SELECT
            id,
            set_number,
            team1_score,
            team2_score,
            winner_id

        FROM match_sets

        WHERE match_id = %s

        ORDER BY set_number
    """, (match_id,))

    scores = cursor.fetchall()

    cursor.close()
    connection.close()


    return render_template(
        "organizer/score_management.html",
        match=match,
        scores=scores
    )


@app.route("/add-announcement", methods=["GET", "POST"])
def add_announcement():

    # Check login
    # Check admin / organizer permission
    if session.get("user_role") not in ["admin", "organizer"]:
        flash(
        "You are not authorized to create announcements.",
        "error"
        )
        return redirect(url_for("announcements"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True,buffered=True)

    # Get tournaments
    cursor.execute("""
        SELECT id, name
        FROM tournaments
        ORDER BY created_at DESC
    """)

    tournaments = cursor.fetchall()

    if request.method == "POST":

        tournament_id = request.form.get("tournament_id")
        title = request.form.get("title", "").strip()
        message = request.form.get("message", "").strip()

        # Get uploaded file
        file = request.files.get("attachment")

        # Basic validation
        if not tournament_id or not title or not message:

            flash(
                "Please fill all required fields.",
                "error"
            )

            cursor.close()
            connection.close()

            return render_template(
                "organizer/add_announcement.html",
                tournaments=tournaments
            )

        attachment_filename = None
        attachment_path = None

        # =====================================
        # FILE UPLOAD
        # =====================================

        if file and file.filename:

            if not allowed_file(file.filename):

                flash(
                    "Invalid file type. "
                    "Allowed: PDF, DOC, DOCX, JPG, JPEG, PNG.",
                    "error"
                )

                cursor.close()
                connection.close()

                return render_template(
                    "organizer/add_announcement.html",
                    tournaments=tournaments
                )

            # Make filename safe
            original_name = secure_filename(
                file.filename
            )

            # Separate filename and extension
            name, extension = os.path.splitext(
                original_name
            )

            # Create unique filename
            filename = (
                f"{name}_{int(time.time())}{extension}"
            )

            # Complete save location
            save_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            # Save file
            file.save(save_path)

            # Save information for database
            attachment_filename = original_name

            attachment_path = (
                f"uploads/announcements/{filename}"
            )

        # =====================================
        # INSERT ANNOUNCEMENT
        # =====================================

        cursor.execute("""
            INSERT INTO announcements
            (
                tournament_id,
                title,
                message,
                created_by,
                attachment_filename,
                attachment_path
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            tournament_id,
            title,
            message,
            session["user_id"],
            attachment_filename,
            attachment_path
        ))

        connection.commit()

        cursor.close()
        connection.close()

        flash(
            "Announcement published successfully.",
            "success"
        )

        return redirect(
            url_for("announcements")
        )

    cursor.close()
    connection.close()

    return render_template(
        "organizer/add_announcement.html",
        tournaments=tournaments
    )




@app.route("/standings/<int:tournament_id>")
def standings(tournament_id):

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )

    # =====================================================
    # GET TOURNAMENT
    # =====================================================

    cursor.execute("""
        SELECT
            id,
            name
        FROM tournaments
        WHERE id = %s
    """, (tournament_id,))

    tournament = cursor.fetchone()

    if not tournament:
        cursor.close()
        connection.close()
        return "Tournament not found", 404


    # =====================================================
    # GET TEAMS
    # =====================================================

    cursor.execute("""
        SELECT
            id,
            team_name
        FROM teams
        WHERE tournament_id = %s
        ORDER BY team_name
    """, (tournament_id,))

    teams = cursor.fetchall()


    # =====================================================
    # INITIALIZE STANDINGS
    # =====================================================

    standings_data = {}

    for team in teams:

        standings_data[team["id"]] = {
            "team_id": team["id"],
            "team_name": team["team_name"],

            "played": 0,
            "won": 0,
            "lost": 0,

            "sets_won": 0,
            "sets_lost": 0,

            "points": 0
        }


    # =====================================================
    # GET COMPLETED MATCHES
    # =====================================================

    cursor.execute("""
        SELECT
            id,
            team1_id,
            team2_id,
            winner_id

        FROM matches

        WHERE tournament_id = %s
          AND status = 'completed'
          AND winner_id IS NOT NULL
    """, (tournament_id,))

    matches = cursor.fetchall()


    # =====================================================
    # PROCESS MATCHES
    # =====================================================

    for match in matches:

        team1_id = match["team1_id"]
        team2_id = match["team2_id"]
        winner_id = match["winner_id"]

        if team1_id not in standings_data:
            continue

        if team2_id not in standings_data:
            continue


        # Played

        standings_data[team1_id]["played"] += 1
        standings_data[team2_id]["played"] += 1


        # Won / Lost

        if winner_id == team1_id:

            standings_data[team1_id]["won"] += 1
            standings_data[team2_id]["lost"] += 1

            # Volleyball points
            standings_data[team1_id]["points"] += 3

        elif winner_id == team2_id:

            standings_data[team2_id]["won"] += 1
            standings_data[team1_id]["lost"] += 1

            # Volleyball points
            standings_data[team2_id]["points"] += 3


        # =================================================
        # GET SETS FOR THIS MATCH
        # =================================================

        cursor.execute("""
            SELECT
                winner_id

            FROM match_sets

            WHERE match_id = %s
        """, (match["id"],))

        match_sets = cursor.fetchall()


        for match_set in match_sets:

            set_winner = match_set["winner_id"]

            if set_winner == team1_id:

                standings_data[team1_id]["sets_won"] += 1
                standings_data[team2_id]["sets_lost"] += 1

            elif set_winner == team2_id:

                standings_data[team2_id]["sets_won"] += 1
                standings_data[team1_id]["sets_lost"] += 1


    # =====================================================
    # CONVERT TO LIST
    # =====================================================

    standings = list(standings_data.values())


    # =====================================================
    # SET DIFFERENCE
    # =====================================================

    for team in standings:

        team["set_difference"] = (
            team["sets_won"] -
            team["sets_lost"]
        )


    # =====================================================
    # SORT STANDINGS
    # =====================================================

    standings.sort(
        key=lambda team: (
            team["points"],
            team["won"],
            team["set_difference"],
            team["sets_won"]
        ),
        reverse=True
    )


    # =====================================================
    # POSITION
    # =====================================================

    for position, team in enumerate(standings, start=1):

        team["position"] = position


    cursor.close()
    connection.close()


    # =====================================================
    # DISPLAY
    # =====================================================

    return render_template(
        "standings.html",
        tournament=tournament,
        standings=standings
    )

# ============================================================
# LIVE SCORE API
# ============================================================

@app.route(
    "/api/organizer/match/<int:match_id>/score/update",
    methods=["POST"]
)
def update_live_score(match_id):

    # --------------------------------------------------------
    # LOGIN CHECK
    # --------------------------------------------------------

    if "user_id" not in session:
        return {
            "success": False,
            "message": "Login required"
        }, 401

    if session.get("user_role") not in ["admin", "organizer"]:
        return {
            "success": False,
            "message": "Unauthorized"
        }, 403


    data = request.get_json()

    if not data:
        return {
            "success": False,
            "message": "No data received"
        }, 400


    try:

        set_number = int(data.get("set_number"))
        team1_score = int(data.get("team1_score"))
        team2_score = int(data.get("team2_score"))

    except (TypeError, ValueError):

        return {
            "success": False,
            "message": "Invalid score"
        }, 400


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if set_number < 1 or set_number > 3:

        return {
            "success": False,
            "message": "Invalid set number"
        }, 400


    if team1_score < 0 or team2_score < 0:

        return {
            "success": False,
            "message": "Score cannot be negative"
        }, 400


    if team1_score == team2_score:

        # During live play, a tie is allowed.
        # Winner will be decided when the set is completed.

        set_winner_id = None

    else:

        set_winner_id = None


    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )


    try:

        # ----------------------------------------------------
        # GET MATCH
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                team1_id,
                team2_id,
                status,
                winner_id
            FROM matches
            WHERE id = %s
        """, (match_id,))

        match = cursor.fetchone()


        if not match:

            return {
                "success": False,
                "message": "Match not found"
            }, 404


        # ----------------------------------------------------
        # FIND EXISTING SET
        # ----------------------------------------------------

        cursor.execute("""
            SELECT id
            FROM match_sets
            WHERE match_id = %s
              AND set_number = %s
        """, (
            match_id,
            set_number
        ))

        existing_set = cursor.fetchone()


        # ----------------------------------------------------
        # INSERT / UPDATE
        # ----------------------------------------------------

        if existing_set:

            cursor.execute("""
                UPDATE match_sets
                SET
                    team1_score = %s,
                    team2_score = %s,
                    winner_id = NULL
                WHERE id = %s
            """, (
                team1_score,
                team2_score,
                existing_set["id"]
            ))

        else:

            cursor.execute("""
                INSERT INTO match_sets
                (
                    match_id,
                    set_number,
                    team1_score,
                    team2_score,
                    winner_id
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    NULL
                )
            """, (
                match_id,
                set_number,
                team1_score,
                team2_score
            ))


        # ----------------------------------------------------
        # MATCH SHOULD BE LIVE
        # ----------------------------------------------------

        cursor.execute("""
            UPDATE matches
            SET status = 'live'
            WHERE id = %s
              AND status NOT IN ('completed', 'cancelled')
        """, (match_id,))


        connection.commit()


        # ----------------------------------------------------
        # GET ALL SETS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                set_number,
                team1_score,
                team2_score,
                winner_id
            FROM match_sets
            WHERE match_id = %s
            ORDER BY set_number
        """, (match_id,))

        sets = cursor.fetchall()


        # ----------------------------------------------------
        # CALCULATE SET WINS
        # ----------------------------------------------------

        team1_sets = 0
        team2_sets = 0

        for match_set in sets:

            if match_set["winner_id"] == match["team1_id"]:

                team1_sets += 1

            elif match_set["winner_id"] == match["team2_id"]:

                team2_sets += 1


        return {
            "success": True,

            "match_id": match_id,

            "team1_sets": team1_sets,

            "team2_sets": team2_sets,

            "sets": sets,

            "status": "live"
        }


    except Exception as e:

        connection.rollback()

        print(
            "LIVE SCORE ERROR:",
            e
        )

        return {
            "success": False,
            "message": "Database error"
        }, 500


    finally:

        cursor.close()
        connection.close()



# ============================================================
# END SET API
# ============================================================

@app.route(
    "/api/organizer/match/<int:match_id>/score/end-set",
    methods=["POST"]
)
def end_live_set(match_id):

    # --------------------------------------------------------
    # LOGIN CHECK
    # --------------------------------------------------------

    if "user_id" not in session:
        return {
            "success": False,
            "message": "Login required"
        }, 401

    if session.get("user_role") not in ["admin", "organizer"]:
        return {
            "success": False,
            "message": "Unauthorized"
        }, 403


    data = request.get_json()

    if not data:
        return {
            "success": False,
            "message": "No data received"
        }, 400


    try:
        set_number = int(data.get("set_number"))
    except (TypeError, ValueError):
        return {
            "success": False,
            "message": "Invalid set number"
        }, 400


    if set_number < 1 or set_number > 3:
        return {
            "success": False,
            "message": "Invalid set number"
        }, 400


    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True,
        buffered=True
    )


    try:

        # ----------------------------------------------------
        # GET MATCH
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                team1_id,
                team2_id,
                status,
                winner_id
            FROM matches
            WHERE id = %s
        """, (match_id,))

        match = cursor.fetchone()


        if not match:
            return {
                "success": False,
                "message": "Match not found"
            }, 404


        # ----------------------------------------------------
        # GET SET
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                set_number,
                team1_score,
                team2_score,
                winner_id
            FROM match_sets
            WHERE match_id = %s
              AND set_number = %s
        """, (
            match_id,
            set_number
        ))

        current_set = cursor.fetchone()


        if not current_set:

            return {
                "success": False,
                "message": "Set score not found"
            }, 404


        team1_score = current_set["team1_score"]
        team2_score = current_set["team2_score"]


        # ----------------------------------------------------
        # SCORES MUST NOT BE EQUAL
        # ----------------------------------------------------

        if team1_score == team2_score:

            return {
                "success": False,
                "message": "Set cannot be ended with equal scores."
            }, 400


        # ----------------------------------------------------
        # DETERMINE SET WINNER
        # ----------------------------------------------------

        if team1_score > team2_score:

            set_winner_id = match["team1_id"]

        else:

            set_winner_id = match["team2_id"]


        # ----------------------------------------------------
        # SAVE SET WINNER
        # ----------------------------------------------------

        cursor.execute("""
            UPDATE match_sets

            SET winner_id = %s

            WHERE id = %s
        """, (
            set_winner_id,
            current_set["id"]
        ))


        connection.commit()


        # ----------------------------------------------------
        # COUNT SET WINS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                winner_id,
                COUNT(*) AS wins

            FROM match_sets

            WHERE match_id = %s
              AND winner_id IS NOT NULL

            GROUP BY winner_id
        """, (match_id,))

        results = cursor.fetchall()


        team1_sets = 0
        team2_sets = 0

        match_winner_id = None


        for result in results:

            if result["winner_id"] == match["team1_id"]:

                team1_sets = result["wins"]

            elif result["winner_id"] == match["team2_id"]:

                team2_sets = result["wins"]


        # ----------------------------------------------------
        # CHECK MATCH WINNER
        # ----------------------------------------------------

        if team1_sets >= 2:

            match_winner_id = match["team1_id"]


        elif team2_sets >= 2:

            match_winner_id = match["team2_id"]


        # ----------------------------------------------------
        # MATCH COMPLETED
        # ----------------------------------------------------

        if match_winner_id:

            cursor.execute("""
                UPDATE matches

                SET
                    winner_id = %s,
                    status = 'completed'

                WHERE id = %s
            """, (
                match_winner_id,
                match_id
            ))

        else:

            cursor.execute("""
                UPDATE matches

                SET status = 'live'

                WHERE id = %s
            """, (match_id,))


        connection.commit()


        # ----------------------------------------------------
        # GET UPDATED SETS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                set_number,
                team1_score,
                team2_score,
                winner_id

            FROM match_sets

            WHERE match_id = %s

            ORDER BY set_number
        """, (match_id,))

        sets = cursor.fetchall()


        return {
            "success": True,

            "match_id": match_id,

            "ended_set": set_number,

            "set_winner_id": set_winner_id,

            "team1_sets": team1_sets,

            "team2_sets": team2_sets,

            "match_winner_id": match_winner_id,

            "status": (
                "completed"
                if match_winner_id
                else "live"
            ),

            "sets": sets
        }


    except Exception as e:

        connection.rollback()

        print(
            "END SET ERROR:",
            e
        )

        return {
            "success": False,
            "message": "Database error"
        }, 500


    finally:

        cursor.close()
        connection.close()



 
if __name__ == "__main__":
    app.run(debug=True)
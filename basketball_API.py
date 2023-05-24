from flask import Flask
import sys
from flask import jsonify, render_template, make_response, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import relationship


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
db = SQLAlchemy(app)


class Teams(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    short = db.Column(db.String(3), unique=True, nullable=False)
    name = db.Column(db.String(50), unique=True, nullable=False)


class Games(db.Model):
    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    home_team_id = db.Column(db.Integer, ForeignKey("teams.id"))
    visiting_team_id = db.Column(db.Integer, ForeignKey("teams.id"))
    home_team_score = db.Column(db.Integer)
    visiting_team_score = db.Column(db.Integer)

    # Relationships
    teams = relationship("Teams")


class Quarters(db.Model):
    __tablename__ = "quarters"
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, ForeignKey("games.id"))
    quarters = db.Column(db.String(50))

    # Relationships
    games = relationship("Games")


def insert_update_query(query):
    db.session.execute(text(query))
    db.session.commit()


def select_query(query):
    return db.session.execute(text(query))


def get_wins(short_name):
    home_query = f"SELECT Count(*) FROM games WHERE home_team_id = (SELECT id FROM teams WHERE short = '{short_name}') " \
                 f"AND home_team_score > visiting_team_score;"

    visiting_query = f"SELECT Count(*) FROM games WHERE visiting_team_id = (SELECT id FROM teams WHERE short = '{short_name}') " \
                     f"AND visiting_team_score > home_team_score;"
    home_count_result = select_query(home_query).fetchone()[0]
    visiting_count_result = select_query(visiting_query).fetchone()[0]

    return home_count_result + visiting_count_result


def get_losses(short_name):
    home_query = f"SELECT Count(*) FROM games WHERE home_team_id = (SELECT id FROM teams WHERE short = '{short_name}') " \
                 f"AND home_team_score < visiting_team_score;"

    visiting_query = f"SELECT Count(*) FROM games WHERE visiting_team_id = (SELECT id FROM teams WHERE short = '{short_name}') " \
                     f"AND visiting_team_score < home_team_score;"
    home_count_result = select_query(home_query).fetchone()[0]
    visiting_count_result = select_query(visiting_query).fetchone()[0]

    return home_count_result + visiting_count_result


# make your code here
@app.route("/", methods=['GET'])
def welcome():
    response = make_response(render_template("index.html"), 200)
    return response


@app.route("/api/v1/teams", methods=['POST', 'GET'])
def team_request():
    if request.method == "POST":
        body_json = request.json
        if body_json['short'].isupper() and len(body_json['short']) == 3:
            query = f"INSERT INTO teams (short, name) VALUES ('{body_json['short']}', '{body_json['name']}');"
            insert_update_query(query)
            response = make_response(jsonify({"success": True, "data": "Team has been added"}), 201)
            return response

        else:
            response = make_response(jsonify({"success": False, "data": "Wrong short format"}), 400)
            return response

    elif request.method == "GET":
        result = select_query("SELECT * FROM teams;")
        rows = result.fetchall()
        result_json = {
                        "success": True,
                        "data": {}
                      }
        for row in rows:
            result_json["data"][row[1]] = row[2]
        response = make_response(result_json, 200)
        return response


@app.route("/api/v1/games", methods=['POST', 'GET'])
def game_request():
    if request.method == "POST":
        body_json = request.json

        home_id_query = f"SELECT id FROM teams WHERE short = '{body_json['home_team']}'"
        visiting_id_query = f"SELECT id FROM teams WHERE short = '{body_json['visiting_team']}'"

        home_id_result = select_query(home_id_query).fetchone()
        visiting_id_result = select_query(visiting_id_query).fetchone()

        if home_id_result is None or visiting_id_result is None:
            response = make_response(jsonify({"success": False, "data": "Wrong team short"}), 400)
            return make_response(response)

        else:
            home_id_result = home_id_result[0]
            visiting_id_result = visiting_id_result[0]

            query = f"INSERT INTO games (home_team_id, visiting_team_id, home_team_score, visiting_team_score) " \
                    f"VALUES ('{home_id_result}', '{visiting_id_result}', '{body_json['home_team_score']}', '{body_json['visiting_team_score']}');"
            insert_update_query(query)
            response = make_response(jsonify({"success": True, "data": "Game has been added"}), 201)
            return response

    elif request.method == "GET":
        result = select_query("SELECT * FROM games;")
        rows = result.fetchall()
        result_json = {
            "success": True,
            "data": {}
        }
        for row in rows:
            home_team_name = select_query(f"SELECT name FROM teams WHERE id = {row[1]};").fetchone()[0]
            visiting_team_name = select_query(f"SELECT name FROM teams WHERE id = {row[2]};").fetchone()[0]

            result_json["data"][row[0]] = f"{home_team_name} {row[3]}:{row[4]} {visiting_team_name}"
        response = make_response(result_json, 200)
        return response


@app.route('/api/v1/team/<short>')
def get_stats(short):
    name_check_query = select_query(f"SELECT name FROM teams WHERE short='{short}'").fetchone()

    if name_check_query is None:
        response = make_response(jsonify({"success": False, "data": f"There is no team {short}"}), 400)
        return response

    else:
        wins = get_wins(short)
        losses = get_losses(short)
        response = make_response(jsonify({"success": True, "data": {"name": name_check_query[0],
                                                                    "short": short,
                                                                    "win": wins,
                                                                    "lost": losses}}), 200)
        return response


@app.route('/api/v2/games', methods=['POST', 'GET'])
def game_v2_request():
    if request.method == "POST":
        body_json = request.json
        home_team = body_json["home_team"]
        visiting_team = body_json["visiting_team"]

        home_id_query = f"SELECT id FROM teams WHERE short = '{home_team}';"
        visiting_id_query = f"SELECT id FROM teams WHERE short = '{visiting_team}';"

        home_id = select_query(home_id_query).fetchone()[0]
        visiting_id = select_query(visiting_id_query).fetchone()[0]

        insert_new_game = f"INSERT INTO games (home_team_id, visiting_team_id, home_team_score, visiting_team_score)" \
                          f"VALUES ('{home_id}', '{visiting_id}', 0, 0);"

        insert_update_query(insert_new_game)

        select_new_id_query = f"SELECT id FROM games;"
        new_id = select_query(select_new_id_query).fetchall()[-1][0]

        response = make_response(jsonify({"success": True, "data": new_id}), 201)

        return response

    elif request.method == "GET":
        select_games_query = "SELECT * FROM games;"
        games_result = select_query(select_games_query).fetchall()
        games_dict = {}

        for game in games_result:
            game_id = game[0]
            home_team_id = game[1]
            visiting_team_id = game[2]
            home_team_score = game[3]
            visiting_team_score = game[4]

            quarters_query = f"SELECT quarters FROM quarters WHERE game_id = '{game_id}';"
            quarters_result = select_query(quarters_query).fetchall()

            home_team_query = f"SELECT name FROM teams WHERE id = '{home_team_id}';"
            visiting_team_query = f"SELECT name FROM teams WHERE id = '{visiting_team_id}';"

            home_team_name = select_query(home_team_query).fetchone()[0]
            visiting_team_name = select_query(visiting_team_query).fetchone()[0]

            game_string = f"{home_team_name} {home_team_score}:{visiting_team_score} {visiting_team_name}"

            if len(quarters_result) != 0:
                quarters_string = "(" + ",".join([result[0] for result in quarters_result]) + ")"
                game_string += f" {quarters_string}"

            games_dict[f"{game_id}"] = game_string

        response = make_response(jsonify({"success": True, "data": games_dict}), 200)

        return response


@app.route('/api/v2/games/<game_id>', methods=["POST"])
def add_quarter(game_id):
    check_query = f"SELECT * FROM games WHERE id = '{game_id}'"
    check_result = select_query(check_query).fetchone()

    if check_result is None:
        response = make_response(jsonify({"success": False, "data": f"There is no game with id {game_id}"}), 400)
        return response
    else:
        body_json = request.json
        quarters = body_json["quarters"]

        add_quarters_query = f"INSERT INTO quarters (game_id, quarters) VALUES ('{game_id}', '{quarters}');"
        insert_update_query(add_quarters_query)

        update_query = f"UPDATE games SET home_team_score = home_team_score + {quarters.split(':')[0]}," \
                                        f"visiting_team_score = visiting_team_score + {quarters.split(':')[1]}" \
                       f" WHERE id = {game_id};"

        insert_update_query(update_query)
        
        response = make_response(jsonify({"success": True, "data": "Score updated"}), 201)
        return response


@app.route('/<path:undefined_route>')
def handle_undefined_route(undefined_route):
    return jsonify({"success": False, "data": "Wrong address"}), 404


# don't change the following way to run flask:
if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()

    if len(sys.argv) > 1:
        arg_host, arg_port = sys.argv[1].split(':')
        app.run(host=arg_host, port=arg_port)
    else:
        app.run(debug=True)

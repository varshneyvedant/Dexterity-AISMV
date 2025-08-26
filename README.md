# Podium - The Winning Live Leaderboard 🏆

Welcome to Podium, the live, real-time web application that was the winning entry for the Sillico Battles v21.1 inter-school competition. This project was developed and deployed under pressure, with features added on the fly based on the judges' requests. It's a testament to rapid, agile, and effective software development.

This document will guide you through exploring the application, both as a live demo and for those who wish to dive into the code.

---

## 🚀 Live Demo

Experience the live, deployed application here: **[[Link to Deployed Site](https://podium-app.onrender.com/)]**

### Exploring the Admin Features

To see the powerful admin and super admin dashboards, which allow for real-time management of the competition, please use the following public demo credentials:

*   **Username:** `demo_super_admin`
*   **Password:** `demo_super_admin`

With these credentials, you can:
*   Add, edit, and delete schools.
*   Manage events and their point values.
*   Submit and edit event results.
*   View a comprehensive audit log of all actions.

The demo database is reset periodically, so feel free to experiment!

---

## ✨ Features

### Public-Facing Features
*   **Live Leaderboard:** A real-time view of school standings, automatically sorted by rank.
*   **Dense Ranking with Advanced Tie-Breaking:**
    *   Schools are ranked using a "dense" system (e.g., 1, 2, 2, 3).
    *   Ties in total points are broken by the number of 1st, then 2nd, then 3rd place finishes.
*   **Visual Highlights:** The top 3 ranked schools are highlighted with gold, silver, and bronze colors.
*   **Visual Podium with Confetti:** A visual representation of the top 3 ranked schools with a celebratory confetti effect.
*   **Detailed School Pages:** Click on a school to see its detailed results and performance summary.
*   **Score Progression Chart:** A dynamic line chart visualizing how school scores have evolved over time.
*   **Download as PDF:** Download the current leaderboard as a PDF document.

### Admin & Super Admin Features
*   **Tiered User Roles:** A secure authentication system with `admin` and `super_admin` roles.
*   **Full Content Management:** Admins can manage schools, events, and results. Super admins can also manage users.
*   **Audit Log:** A comprehensive log that tracks all significant actions.
*   **Predictive Analytics:** A feature to forecast the top contenders based on current performance.

---

## 🛠️ Technology Stack

*   **Backend:** Python (Flask)
*   **Database:** SQLite
*   **Frontend:** HTML, CSS, JavaScript, Jinja2
*   **PDF Generation:** `pdfkit`
*   **Password Security:** Passwords are securely hashed using the `scrypt` algorithm via `Werkzeug`.

---

## 👨‍💻 For Developers: Running Locally

For those who wish to dive into the code and run the project on their own machine.

### Step 1: Get the Code
```bash
git clone https://github.com/varshneyvedant/podium-app.git
cd podium-app
```

### Step 2: Set Up a Virtual Environment
```bash
# For macOS/Linux
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```
*Note: The "Download as PDF" feature requires `wkhtmltopdf` to be installed on your system. You can download it from [here](https://wkhtmltopdf.org/downloads.html).*

### Step 4: Initialize the Database
The first time you run the application, the database needs to be created and seeded with sample data.
```bash
flask init-db
```
This will create a `podium.db` file and populate it with sample schools, events, and a `demo_super_admin` user.

### Step 5: Run the Application
```bash
flask run
```
The application will be available at `http://127.0.0.1:5000`. You can log in with the `demo_super_admin` credentials mentioned in the "Live Demo" section.

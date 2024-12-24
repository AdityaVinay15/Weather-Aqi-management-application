from flask import Flask, flash, url_for, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from forms import CarbonFootprintForm
import requests
import pandas as pd
import plotly.express as px
from flask_mail import Mail, Message
from flask_migrate import Migrate

app = Flask(__name__, static_folder='static', template_folder='templates')


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key_here' 
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Change this to your email provider
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'Nagasaibh10@gmail.com'  # Your email
app.config['MAIL_PASSWORD'] = 'Nagasaibh' 

# Initialize SQLAlchemy
db = SQLAlchemy(app)
mail = Mail(app)


# # Initialize Flask-Migrate
# migrate = Migrate(app, db)

# Database model for User
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)

    def __init__(self, username, password,email,city): 
        self.username = username
        self.email = email
        self.password = password
        self.city = city

class Leaderboard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    carbon_footprint = db.Column(db.Float, nullable=False)
    rank = db.Column(db.Integer, nullable=False)
    city= db.Column(db.String(100), nullable=False)

    def __init__(self, name, carbon_footprint, rank, city):
        self.name = name
        self.carbon_footprint = carbon_footprint
        self.rank = rank
        self.city = city
        
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True)
    image = db.Column(db.String(100), nullable=True) 
    likes = db.Column(db.Integer, default=0)
    def __init__(self, title, content, user_id, image=None):
        self.title = title
        self.content = content
        self.user_id = user_id
        self.image = image

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __init__(self, user_id,content, post_id):
        self.content = content
        self.post_id = post_id
        self.user_id = user_id

@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post(post_id):
    post = Post.query.get(post_id)
    if request.method == 'POST':
        comment_content = request.form['comment']
        user_id = User.query.filter_by(username=session['username']).first().id
        new_comment = Comment(content=comment_content, post_id=post_id, user_id=user_id)
        db.session.add(new_comment)
        db.session.commit()

        # Send email to the post creator
        post_creator = User.query.get(post.user_id)
        send_email(post_creator.email, post.title, comment_content)

        flash('Comment posted successfully!', 'success')
        return redirect(url_for('post', post_id=post_id))
    return render_template('post.html', post=post)

# Email function to notify post creator
def send_email(to_email, post_title, comment_content):
    try:
        msg = Message('New Comment on Your Post',
                      sender='Nagasaibh10@gmail.com',
                      recipients=[to_email])
        msg.body = f"Someone commented on your post titled '{post_title}':\n\n{comment_content}"
        mail.send(msg)
    except Exception as e:
        print(f"Error sending email: {e}")

@app.route('/community')
def community():
    # Fetch posts from the database
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template('posts.html', posts=posts)

import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/createpost', methods=['GET', 'POST'])
def create_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        
        # Handle image upload
        image = None
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image_file.save(image_path)
                image = image_path  # Store the image path in the database
        
        # Create a new post with or without an image
        new_post = Post(title=title, content=content, user_id=session['username'], image=image)
        db.session.add(new_post)
        db.session.commit()
        flash('Post created successfully!', 'success')
        return redirect(url_for('community'))

    return render_template('createpost.html')

@app.route('/like-post/<int:post_id>/', methods=['POST'])
def like_post(post_id):
    post = Post.query.get(post_id)
    if post:
        post.likes = (post.likes or 0)+1
        db.session.commit()
        return redirect(request.referrer or url_for('home'))
    else:
        return "Post not found", 404
@app.route('/submit-comment/<int:post_id>/', methods=['POST'])
def submit_comment(post_id):
    post = Post.query.get(post_id)
    if not post:
        return "Post not found", 404

    comment_text = request.form.get('comment_text')
    if not comment_text:
        return "Comment cannot be empty", 400
    author=session['username']
    # Create a new comment
    new_comment = Comment(author=session['username'], content=comment_text, post_id=post.id)
    db.session.add(new_comment)
    db.session.commit()

    return redirect(request.referrer or url_for('home'))

apikey='39c61348f6876b9d859b9b446d52d31f'
aqi_apikey="132f67be1b7c0decb2f2135bafb77d0f692bec9a"
news_apikey="pub_60511d17f059f10184deec9ad9f0109e46cf2"
# fetching dashboard
def fetch_dashboard_data(city='Hyderabad'):
    weather = {}
    aqi = "N/A"
    aqi_status = "N/A"
    news = []

    # Fetch weather data
    try:
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={apikey}&units=metric"
        weather_response = requests.get(weather_url).json()
        # Fetch timezone information from the weather API response
        timezone_offset = weather_response['timezone']
        sunrise_time = datetime.utcfromtimestamp(weather_response['sys']['sunrise'] + timezone_offset)
        sunset_time = datetime.utcfromtimestamp(weather_response['sys']['sunset'] + timezone_offset)
        weather = {
            'city': city,
            'temperature': weather_response['main']['temp'],
            'feels_like': weather_response['main']['feels_like'],
            'humidity': weather_response['main']['humidity'],
            'pressure': weather_response['main']['pressure'],
            'wind_speed': weather_response['wind']['speed'],
            'visibility': weather_response['visibility'] / 1000,
            'sunrise': sunrise_time.strftime('%I:%M:%S %p'),  
            'sunset': sunset_time.strftime('%I:%M:%S %p'),
        }
    except Exception as e:
        print("Error fetching weather:", e)
        weather['error'] = "Error retrieving weather data"

    #Fetching AQI data
    try:
        aqi_url = f"https://api.waqi.info/feed/{city}/?token={aqi_apikey}"
        aqi_response = requests.get(aqi_url).json()

        if aqi_response.get('status') == 'ok':
            aqi_data = aqi_response.get('data', {})
            aqi = aqi_data.get('aqi', 'N/A')

            if aqi != "N/A":
                if aqi <= 50:
                    aqi_status = "Good"
                elif aqi <= 100:
                    aqi_status = "Moderate"
                elif aqi <= 150:
                    aqi_status = "Unhealthy for Sensitive Groups"
                elif aqi <= 200:
                    aqi_status = "Unhealthy"
                elif aqi <= 300:
                    aqi_status = "Very Unhealthy"
                else:
                    aqi_status = "Hazardous"
    except Exception as e:
        print("Error fetching AQI data:", e)

    #Fetching news data
    try:
        news_url = f"http://newsdata.io/api/1/news?apikey={news_apikey}&q={city}&language=en"
        news_response = requests.get(news_url).json()

        if 'results' in news_response:
            news = [{'title': article['title'], 'link': article['link'], 'image': article.get('image_url')}
                    for article in news_response['results'] if 'title' in article]
    except Exception as e:
        print("Error fetching news:", e)

    return {
        'weather': weather,
        'aqi': f"{aqi} ({aqi_status})",
        'news': news
    }

@app.route('/')
def dashboard():
    city = request.args.get('city', 'Hyderabad')
    data = fetch_dashboard_data(city)
    return render_template('index.html', **data)


# Register route
@app.route('/register/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email    = request.form['email']
        city     = request.form['city']
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('register.html', message="User Already Exists")
        try:
            new_user = User(username=username, password=password, email=email, city=city)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except Exception as e:
            return render_template('register.html', message="User Already Exists or Invalid Data")
    return render_template('register.html')


# Login route
@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        data = User.query.filter_by(email=email, password=password).first()

        if data:
            session['logged_in'] = True
            session['username'] = data.username  # Store the username in session
            session['city'] = data.city
            dashboard_data = fetch_dashboard_data(session['city'])
            return render_template('index.html', email=email, **dashboard_data)
        else:
            flash('Invalid login credentials, please try again.', 'error')

    return render_template('login.html')



@app.route('/logout')
def logout():
    session.clear()  # Clear the session data
    city = 'Hyderabad'  # Default city or you can use a different logic
    dashboard_data = fetch_dashboard_data(city)  # Fetch dashboard data for the default city
    return render_template('index.html', **dashboard_data)


@app.route('/carbontracker', methods=['GET', 'POST'])
def carbon_footprint():
    form = CarbonFootprintForm()
    if form.validate_on_submit():
        # Process the form data
        transport_emissions = form.distance.data * 0.1  # Replace with actual emission factor for transport mode
        daily_usage = form.today_usage.data - form.prev_usage.data
        electricity_emissions = daily_usage * 0.5  # Replace with actual emission factor
        dry_waste_emissions = form.dry_waste.data * 0.1  # Replace with actual emission factor
        wet_waste_emissions = form.wet_waste.data * 0.2  # Replace with actual emission factor

        # Calculate total carbon footprint
        carbon_footprint = transport_emissions + electricity_emissions + dry_waste_emissions + wet_waste_emissions

        # Fetch user data
        username = session.get('username', 'Anonymous')
        user_city = session.get('city', 'Unknown')

        # Leaderboard logic
        leaderboard_entries = Leaderboard.query.all()
        leaderboard_entries_sorted = sorted(leaderboard_entries, key=lambda entry: entry.carbon_footprint)

        # Calculate rank: the person with the lowest carbon footprint gets rank 1
        rank = 1 + sum(entry.carbon_footprint < carbon_footprint for entry in leaderboard_entries_sorted)

        new_entry = Leaderboard(name=username, carbon_footprint=carbon_footprint, rank=rank, city=user_city)
        db.session.add(new_entry)
        db.session.commit()

        # Render result
        return render_template('result.html', carbon_footprint=carbon_footprint)
    else:
        print("Form not submitted or invalid")
    return render_template('carbonfootprinttracker.html', form=form)




@app.route("/leaderboard")
def show_leaderboard():
    # Retrieve all leaderboard entries and sort them by carbon_footprint in descending order
    leaderboard_entries = Leaderboard.query.order_by(Leaderboard.carbon_footprint.desc()).all()
    return render_template("leaderboard.html", leaderboard=leaderboard_entries)

@app.route('/visualize')
def visualize():
    historical_data=pd.DataFrame({
        'Date':pd.date_range('2022-01-01',periods=10,freq='D'),
        'CarbonEmission':[100,150,200,250,300,350,400,450,500,550]})
    if historical_data.empty:
        return "No data avilable for visualization"
    fig=px.line(historical_data,x="Date",y="CarbonEmission",title="Carbon Emission Trends Over Time")
    fig_html=fig.to_html(full_html=False)
    return render_template('visualize.html',plot_html=fig_html)

# Main block to create database and run the app
if __name__ == '__main__':
    with app.app_context():
        print("Creating database...")
        db.create_all()
        print("Database created!")
    app.run(debug=True)


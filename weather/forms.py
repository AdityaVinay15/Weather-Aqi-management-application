from flask import Flask, render_template, request, session, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key

class CarbonFootprintForm(FlaskForm):
    # Transportation
    distance = IntegerField('Distance (km):', validators=[DataRequired()])
    mode = SelectField('Mode of Transport:', 
                       choices=[('car', 'Car'), ('bus', 'Bus'), ('train', 'Train'), 
                                ('bike', 'Bike'), ('walk', 'Walk')],
                       validators=[DataRequired()])
    
    # Electricity
    prev_usage = IntegerField('Previous Month Usage (kWh):', validators=[DataRequired()])
    today_usage = IntegerField('Today\'s Usage (kWh):', validators=[DataRequired()])
    
    # Waste
    dry_waste = IntegerField('Dry Waste (kg):', validators=[DataRequired()])
    wet_waste = IntegerField('Wet Waste (kg):', validators=[DataRequired()])
    
    # Submit button
    submit = SubmitField('Calculate Carbon Footprint')



if __name__ == '__main__':
    app.run(debug=True)

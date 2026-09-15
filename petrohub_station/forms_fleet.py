from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class FleetOrderForm(FlaskForm):
    vehicle_type = SelectField("Vehicle Type", choices=[
        ("Tanker", "Petroleum Tanker"),
        ("Trailer", "Trailer"),
        ("Small Truck", "Small Capacity Truck")
    ], validators=[DataRequired()])
    quantity = IntegerField("Quantity", validators=[DataRequired(), NumberRange(min=1)])
    destination = StringField("Destination", validators=[DataRequired()])
    submit = SubmitField("Submit Request")

from flask import Flask, Markup, render_template, request
import mysql.connector

app = Flask(__name__)

mydb = mysql.connector.connect(
    host="192.168.0.6",
    user="renaud",
    passwd="d40;B64!",
    database="jardin"
    )
          
mycursor = mydb.cursor()
          
class data:
    def __init__(self, backgroundColor, borderColor, nom, values):
	self.backgroundColor: window.chartColors.red,
	self.borderColor: window.chartColors.red
        self.nom = nom
        self.values = values
                                                                
@app.route('/bar')
def bar():
    bar_labels=labels
    bar_values=values
    return render_template('bar_chart.html', title='Bitcoin Monthly Price in USD', max=17000, labels=bar_labels, values=bar_values)

@app.route('/line')
def line():
    labels=[1,2]
    values=[2,5]
    line_labels=labels
    line_values=values
    return render_template('line_chart.html', title='Bitcoin Monthly Price in USD', max=5, labels=line_labels, values=line_values)

@app.route('/pie')
def pie():
    pie_labels = labels
    pie_values = values
    return render_template('pie_chart.html', title='Bitcoin Monthly Price in USD', max=17000, set=zip(values, labels, colors))

@app.route('/', methods= ['POST', 'GET'])
def temperature_humidite():
    Temps=[]
    Humidite_values=[]
    Temperature_values=[]
    mycursor.execute("SELECT * FROM Temperature_Humidite")
    myresult = mycursor.fetchall()
    pas=int(len(myresult)/40)
    print(pas)
    for i,x in enumerate(myresult):
        if i%pas==0:
            Temps.append(x[1])
            Humidite_values.append(x[2])
            Temperature_values.append(x[3])
    allume=0
    if request.method == 'POST':
        if request.form.getlist('allume') == ['on']:
            allume=1
        else:
            allume=0
    line_labels=Temps
    Temperature=data("rgba(186,125,125,1)","rgba(186,125,125,1)",'Température',Temperature_values)
    Humidite=data("rgba(151,187,205,1)","rgba(151,187,205,1)",'Humidité',Humidite_values)
    line_values=[Temperature,Humidite]

    return render_template('temp_humid_chart.html', title='Température et Humidité', max=100, labels=line_labels, datasets=line_values, allume=allume)
            

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

#!/usr/bin/env python

import sys, os, csv, re, argparse
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

# Access data for JHU Github
JHUGithub = "https://github.com/CSSEGISandData/COVID-19.git"
BasePathTimeSeries = "COVID-19/csse_covid_19_data/csse_covid_19_time_series"
BasePathDailyReports = "COVID-19/csse_covid_19_data/csse_covid_19_daily_reports"

# Some keys
PartConfirmed = "Confirmed"
PartDeaths = "Deaths"
PartRecovered = "Recovered"

def findInPath(program):
    for path in os.environ["PATH"].split(os.pathsep):
        executable = os.path.join(path, program)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return executable
    return None
    
def findOrca():
    orcaExecutable = findInPath("orca")
    if orcaExecutable is None and sys.platform == "darwin":
        orcaExecutable = "/Applications/orca.app/Contents/MacOS/orca"
        if not os.path.exists(orcaExecutable):
            orcaExecutable = None

    if orcaExecutable is None:
        print("Could not find Orca, which needs to be installed.")
        sys.exit(-1)
    else:
        pio.orca.config.executable = orcaExecutable

def checkIfRepoExists():
    if (not os.path.exists("COVID-19") or
        not os.path.isdir("COVID-19") or
        not os.path.exists("COVID-19/.git")):
        print("No git repo at ./COVID-19.")
        return -1
    else:
        return 0

def cloneRepo():
    if os.system("git clone " + JHUGithub) != 0:
        sys.exit("Could not clone JHU github repo at" + JHUGithub)
    return 0

def updateRepo():
    if os.system("(cd COVID-19; git pull)") != 0:
        sys.exit("Could not pull git repo.")
    return 0

def average(array):
    # helper to average n numbers. Yes, could use numpy.
    result = float(array[0])
    for val in array[1:]:
        result += float(val)
    return result / len(array)

def readDataFromTimeSeries(part, country, start):
    # this is not used at the moment, as the last and last-but-one days in each time series
    # produce the same data
    with open(BasePathTimeSeries + '/time_series_19-covid-' + part + '.csv', mode='r') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        row0 = None
        startindex = 5
        
        for row in csv_reader:
            if line_count == 0:
                row0 = row
                try:
                    startindex = row0.index(start)
                except:
                    print(start, "not found")
                    
            elif row[1] == country:
                return row0[startindex:], row[startindex:]
            line_count += 1

def readDataFromDailyReports(part, country, start):
    # Need to sort file list first. Damn Americans - who writes dates MM-DD-YYYY? How are you supposed
    # to sort this stuff?
    
    regex = "^(\d\d)\-(\d\d)\-(\d\d\d\d)$"
    filelist = os.listdir(BasePathDailyReports)
    filelist = [os.path.splitext(x)[0] for x in filelist]
    filelist = [tuple(map(int, re.match(regex, x).groups())) for x in filelist if re.match(regex, x) is not None]
    filelist = sorted(filelist, key=lambda tuple: "%04d%02d%02d" % (tuple[2], tuple[0], tuple[1]))
    filelist_slashes = ["%02d/%02d/%02d" % (x[0], x[1], x[2]-2000) for x in filelist]
    startindex = filelist_slashes.index(start)
    filelist = filelist[startindex:]

    data = []
    for filename_tuple in filelist:
        csv_file = open(BasePathDailyReports + "/%02d-%02d-%04d.csv" % filename_tuple, mode="r")
        csv_reader = csv.reader(csv_file, delimiter=",")
        row0 = next(csv_reader)
        col_country = [i for i, item in enumerate(row0) if re.search('^Country', item)][0]
        col_data = row0.index(part)
        found = False
        for row in csv_reader:
            if row[col_country] == country:
                found = True
                data.append(row[col_data])
                break
        if not found:
            print(country, "not found in %02d-%02d-%04d.csv" % filename_tuple)
            data.append[0]
    return(["%04d-%02d-%02d" % (x[2], x[0], x[1]) for x in filelist], data)
    
def analyzeData(rowData):
    percIncrease = [0,]
    for i in range(1, len(rowData)):
        if float(rowData[i-1]) == 0:
            percIncrease.append(0)
        else:
            percIncrease.append(((float(rowData[i]) / float(rowData[i-1])) - 1)*100)
    avgPercIncrease = [0, 0, 0, 0]
    for i in range(4, len(percIncrease)):
        avgPercIncrease.append(average(percIncrease[i-4:i]))
    return percIncrease, avgPercIncrease
            
def graphData(part, country, startdate, title):
    rowAxis, rowData = readDataFromDailyReports(part, country, startdate)
    percIncrease, avgPercIncrease = analyzeData(rowData)
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(x=rowAxis, y=rowData, text=rowData, name=part,
                             mode="lines+text", textposition="top center",
                             textfont=dict(size=10)),
                  secondary_y=False)
    fig.update_yaxes(title_text="Absolute Cases", secondary_y=False)

    fig.add_trace(go.Scatter(x=rowAxis, y=avgPercIncrease, text = ["%.1f%%" % x for x in avgPercIncrease],
                             name="% Increase", mode="lines+text", textposition="top center",
                             textfont=dict(size=10)),
                  secondary_y=True)
    fig.update_yaxes(title_text="%increase (5-day avg)", secondary_y=True)

    fig.update_layout(title_text=title)
    fig.update_xaxes(title_text="Date")
    fig.write_image(title + "." + pio.renderers.default, scale=2)

if __name__=="__main__":
    parser = argparse.ArgumentParser(description = "Report COVID-19 data.")
    parser.add_argument("-c", "--country", default="Germany",
                        help="Country to process. Note that multi-region countries "
                        "are currently not supported.")
    parser.add_argument("--startdate", default="02/20/20",
                        help="Start date, MM/DD/YY format. Yeah I know.")
    parser.add_argument("--updategit", choices=["true", "false"], default="true",
                        help="Update Git data (or clone if not cloned yet)")
    parser.add_argument("--format", choices=["png", "pdf", "jpg"], default="png",
                        help="File format for the generated plots.")
    args = parser.parse_args()

    print("Generating data for", args.country, "from", args.startdate, "until today.")
    pio.renderers.default = args.format
    print("Using", args.format, "output file format.")
    
    findOrca()

    if(args.updategit == "true"):
        if checkIfRepoExists() != 0:
            print("Cloning JHU repository.")
            cloneRepo()
        else:
            print("Updating JHU repository.")
            updateRepo()

    print("Graphing", PartConfirmed)
    graphData(PartConfirmed, args.country, args.startdate, "Confirmed Cases "+args.country)
    print("Graphing", PartRecovered)
    graphData(PartRecovered, args.country, args.startdate, "Recovered "+args.country)
    print("Graphing", PartDeaths)
    graphData(PartDeaths, args.country, args.startdate, "Deaths "+args.country)
        

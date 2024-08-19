from fasthtml.common import *
from dataclasses import dataclass
import json

@dataclass
class Chart:
    data: list
    auto: list
    exp: list
    start_date: str
    end_date: str
    
    js = '''
    document.addEventListener("DOMContentLoaded", function() {
        var options = {
            series: [
                {
                name: 'Real Data',
                data: DATA_PLACEHOLDER
                },
                {
                name: 'Auto Regression Predictions',
                data: AUTO_PLACEHOLDER
                },
                {
                name: 'Exponential Smoothing Predictions',
                data: EXP_PLACEHOLDER
                }
            ],
            chart: {
                id: 'chart2',
                type: 'line',
                height: 300,
                toolbar: {
                    autoSelected: 'pan',
                    show: false
                }
            },
            colors: ['#FF003B','#008FFB', '#00E396'],
            tooltip: {
                enabled: true,
                shared: true,
                marker: {
                    show: true
                }
            },
            xaxis: {
                type: 'datetime'
            },
            yaxis: {
                min: 0
            }
        };

        var chart = new ApexCharts(document.querySelector("#chart-line2"), options);
        chart.render();
      
        var optionsLine = {
            series: [
                {
                name: 'Real Data',
                data: DATA_PLACEHOLDER
                },
                {
                name: 'Auto Regression Predictions',
                data: AUTO_PLACEHOLDER
                },
                {
                name: 'Exponential Smoothing Predictions',
                data: EXP_PLACEHOLDER
                }
            ],
            chart: {
                id: 'chart1',
                height: 200,
                type: 'line',
                brush:{
                    target: 'chart2',
                    enabled: true
                },
                selection: {
                    enabled: true,
                    xaxis: {
                        min: new Date('START_DATE').getTime(),
                        max: new Date('END_DATE').getTime()
                    }
                },
            },
            colors: ['#FF003B', '#008FFB', '#00E396'],
            stroke: {
                width: 1
            },
            xaxis: {
                type: 'datetime'
            },
            yaxis: {
                tickAmount: 4,
                min:0
            },
            dataLabels: {
                enabled: false
            },
            legend: {
                show: false
            }
        };

        var chartLine = new ApexCharts(document.querySelector("#chart-line"), optionsLine);
        chartLine.render();
    });
    '''
    
    def __ft__(self):
        self.js = self.js.replace('DATA_PLACEHOLDER', json.dumps(self.data))
        self.js = self.js.replace('AUTO_PLACEHOLDER', json.dumps(self.auto))
        self.js = self.js.replace('EXP_PLACEHOLDER', json.dumps(self.exp))
        self.js = self.js.replace('START_DATE', self.start_date)
        self.js = self.js.replace('END_DATE', self.end_date)
        # print(self.js)
        return Script(self.js)
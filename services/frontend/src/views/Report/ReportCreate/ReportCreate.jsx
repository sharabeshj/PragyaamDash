import React from 'react';
import Axios from 'axios';
import {withStyles} from '@material-ui/core/styles';
import ChartistGraph from 'react-chartist';
import {connect} from 'react-redux';

import BarChart from '@material-ui/icons/BarChart';
import ShowChart from '@material-ui/icons/ShowChart';
import Sort from '@material-ui/icons/Sort';
import ViewList from '@material-ui/icons/ViewList';
import ViewModule from '@material-ui/icons/ViewModule';
import PieChart from '@material-ui/icons/PieChart';
import DonutLarge from '@material-ui/icons/DonutLarge';
import ScatterPlot from '@material-ui/icons/ScatterPlot';
import ZoomOutMap from '@material-ui/icons/ZoomOutMap';

import GridContainer from '../../../components/Grid/GridContainer';
import GridItem from '../../../components/Grid/GridItem';
import Card from '../../../components/Card/Card';
import CardHeader from '../../../components/Card/CardHeader';
import CardIcon from '../../../components/Card/CardIcon';
import CardBody from '../../../components/Card/CardBody';
import CardFooter from '../../../components/Card/CardFooter';
import ReportToolbar from "../../../components/ReportToolbar/ReportToolbar";
import Aux from '../../../hoc/aux/aux';
import Danger from '../../../components/Typography/Danger';
import FilterOptions from '../../../components/FilterOptions/FilterOptions';
import Graph from '../../../components/Graph/Graph';

import { handleDataLoad, handleDefaultDataLoad, handleClearReportData } from '../../../store/Actions/ActionCreator'

import {
    roundedLineChart,
    straightLinesChart,
    simpleBarChart,
    colouredLineChart,
    multipleBarsChart,
    colouredLinesChart,
    pieChart,
    stackedBarChart,
    stackedHorBarChart,
    donutChart
  } from "variables/charts.jsx";

import {
    barChartDemo,
    lineChartDemo,
    pieChartDemo,
    radarChartDemo,
    polarChartDemo,
    bubbleChartDemo,
    mixedChartdemo,
    donutChartDemo,
    horBarChartDemo
} from '../../../variables/graphs';

import radar from '../../../assets/img/radar.png';
import chartPie from '../../../assets/img/chart-pie.png';
import chartBubble from '../../../assets/img/chart-bubble.png';
import chartMultiline from '../../../assets/img/chart-multiline.png';

import reportCreateStyle from '../../../assets/jss/frontend/views/reportCreateStyle';

let resetFunc;

class ReportCreate extends React.Component{
    constructor(){
        super();
        this.state = {
            datasets : [],
            fields : [],
            reportTitle : '',
            reportType: '',
            reportDescription : '',
            selectedFields : [],
            selectedXField : '',
            selectedYField : '',
            selectedDataset :  '',
            reportOptions : {},
            reportListeners : {},
            filterChecked : false,
            selectedOperation : '',
            selectedGroupBy : '',
            selectedMeasureOperation : 'LAST'
        };
        this.ref = React.createRef();
        // this.resetFunc.bind(this);
    };

    // resetFunc = () => {}

    componentDidMount(){
        this.getDatasets();
    }

    getDatasets = () => {
        Axios.get(`${process.env.REACT_APP_API_URL}/datasets/`)
        .then(res => {
            this.setState({ datasets : [...res.data]})
        }); 
    };

    componentWillUnmount(){
        this.props.handleClearReportData();
    }

    handleDatasetChange = (e) => {
        console.log(e.currentTarget, typeof(e.target.value));
        e.persist();
        this.setState(prevState => {
            let newFields = [];
            for(let i=0; i < prevState.datasets.length; i++){
                console.log(e.target.value);
                if(prevState.datasets[i].dataset_id == e.target.value){
                    newFields = prevState.datasets[i].fields;
                    break;
                }
            }
            return { selectedDataset : e.target.value, fields : newFields}
        });
    };

    handleChange =  name => (e) => {
        console.log(e.currentTarget.value);
        this.setState({ [name] : e.currentTarget.value })
    }

    handleGraphChange = e => {
        const defaultData = this.getDefaultGraph(e.currentTarget.value);
        this.setState({
            ...defaultData
        });
    }

    getDefaultGraph = name =>  {
        switch(name){
            case 'bar':
                this.props.handleDefaultDataLoad(barChartDemo, name);
                return {
                    reportType : name,
                    icon : (<BarChart/>),
                    reportOptions : barChartDemo.options,
                }
            case "line":
                this.props.handleDefaultDataLoad(lineChartDemo, name);
                return {
                    reportType : name,
                    icon : (<ShowChart />),
                    reportOptions : lineChartDemo.options,
                }
            case "StackedBar":
                this.props.handleDefaultDataLoad(stackedBarChart, "Bar");
                return {
                    reportType : "Bar",
                    icon : (<ViewModule/>),
                    reportOptions : stackedBarChart.options,
                    reportListeners : stackedBarChart.animation
                }
            case "StackedHorBar":
                this.props.handleDefaultDataLoad(stackedHorBarChart, "Bar");
                return {
                    reportType : "Bar",
                    icon : (<ViewList />),
                    reportOptions : stackedHorBarChart.options,
                    reportListeners : stackedHorBarChart.animation
                }
            case "pie":
                this.props.handleDefaultDataLoad(pieChartDemo, name);
                return {
                    reportType : name,
                    icon : (<PieChart/>),
                    reportOptions : pieChartDemo.options
                }
            case "doughnut":
                this.props.handleDefaultDataLoad(donutChartDemo, name);
                return {
                    reportType : name,
                    icon : (<DonutLarge/>),
                    reportOptions : donutChartDemo.options
                }
            case 'radar':
                this.props.handleDefaultDataLoad(radarChartDemo, name);
                return {
                    reportType : name,
                    icon : (<img src = {radar} alt={"radar-graph"}/>),
                    reportOptions : radarChartDemo.options
                }
            case 'polarArea':
                this.props.handleDefaultDataLoad(polarChartDemo, name);
                return {
                    reportType : name,
                    icon : (<img src = {chartPie} alt={"polar-graph"}/>),
                    reportOptions : polarChartDemo.options
                }
            case 'horizontalBar':
                this.props.handleDefaultDataLoad(horBarChartDemo, name);
                return {
                    reportType : name,
                    icon : (<Sort />),
                    reportOptions : horBarChartDemo.options
                }
            case 'bubble':
                this.props.handleDefaultDataLoad(bubbleChartDemo, name);
                return {
                    reportType : name,
                    icon : (<img src = {chartBubble} alt={"bubble-graph"}/>),
                    reportOptions : bubbleChartDemo.options
                }
            case 'bar_mix':
                this.props.handleDefaultDataLoad(mixedChartdemo, "bar");
                return {
                    reportType : name,
                    icon : (<img src = {chartMultiline} alt={"mixed-graph"}/>),
                    reportOptions : mixedChartdemo.options
                }
            default:
                return {}
        }
    }

    handleFieldChange  = (xField,yField) => {
        if(yField === null) {
            this.setState(prevState => {
                const newSelectedFields = [...prevState.selectedFields];
                newSelectedFields[0] = xField;
                return{
                selectedFields : newSelectedFields,
                selectedXField : xField
            }});
        }
        else {
            this.setState(prevState => {
                const newSelectedFields = [...prevState.selectedFields];
                newSelectedFields[1] = yField
                return {
                selectedFields : newSelectedFields,
                selectedYField : yField
            }});
        }
    };

    handleCancel = () => {
        this.props.handleClearReportData();
        this.setState({ fields : [],
            reportTitle : '',
            reportType: '',
            selectedFields : [],
            selectedXField : '',
            selectedYField : '',
            selectedDataset :  '',
            selectedGroupBy : ''
        });
    }

    handleLoad = () => {
        const postData = {
                'type' : this.state.reportType,
                'dataset' : this.state.selectedDataset,
                'options' : {
                    'X_field' : this.state.selectedXField,
                    'Y_field' : this.state.selectedYField,
                    'group_by' : this.state.selectedGroupBy,
                    'measure_operation' : this.state.selectedMeasureOperation
                },
                'reportDescription' : this.state.reportDescription
        }
        this.props.handleDataLoad(postData);
    }

    handleFilterToggle = () => {
        this.setState(prevState => ({ filterChecked : !prevState.filterChecked }));
    }

    handleFilterOptions = (state) => {
        this.setState(prevState => {
            const new_report_data = {
                ...prevState.report_data,
                labels : [...prevState.report_data.labels].slice(state.xRange[0],state.xRange[1]+1)
            };
            for(let i=0;i < new_report_data.series.length; i++){
                new_report_data.series[i] = [...new_report_data.series[i]].slice(state.yRange[0], state.yRange[1] +1)
            }
            return { report_data : new_report_data, selectedOperation : state.selectedOperation }
        })
    }

    handleSave = () => {
        const postData = {
            url : `${process.env.REACT_APP_API_URL}/reports/`,
            method: 'POST',
            data: this.convert_func_in_json({
                'dataset_id' : this.state.selectedDataset,
                'data' : {
                    'report_type' : this.props.options.type,
                    'report_title' : this.state.reportTitle,
                    'report_description' : this.state.reportDescription,
                    'reported' : false,
                    'initial' : true,
                    'report_options' : {
                        ...this.props.options
                    }
                }
            }),
            headers : {
                'Content-Type' : 'application/json',
                'Authorization' : `Token ${this.props.auth_token}`
            }
        }
        Axios(postData)
        .then(res => this.props.history.push('/reports/list'))
    }

    handleGroupByChange = value => {
        this.setState({ selectedGroupBy : value });
    }

    handleMeasureOperation = op => {
        this.setState({ selectedMeasureOperation : op });
    }

    convert_func_in_json = obj => {
        return JSON.stringify(obj, (key, value) => {
            return typeof value === "function" ? value.toString() : value;
        });
    }

    render(){
        let report_data = null;
        const {classes} = this.props;
        if(Object.keys(this.props.reportData).length !== 0 && this.props.reportData.constructor === Object){
            report_data = (<GridContainer>
                <GridItem xs={12} sm={12} md={6}>
                <Card>
                    <CardHeader color="success" icon>
                        <CardIcon color="success">
                            {this.state.icon}
                        </CardIcon>
                        <h4 className={classes.cardIconTitle}>
                            {this.state.reportTitle}
                        </h4>
                    </CardHeader>
                    <Graph
                        data={this.props.reportData}
                        type={this.props.options.type}
                        options={this.props.options.reportOptions}
                        width = {500}
                        height = {500}
                    />
                </Card>
                </GridItem>
                <GridItem xs={12} sm={12} md={6}>
                    <FilterOptions 
                        yLen={this.props.reportData.datasets.length}
                        xLen={this.props.reportData.labels.length}
                        filterChecked = {this.state.filterChecked}
                        handleFilterToggle={this.handleFilterToggle}
                        handleFilterOptions={this.handleFilterOptions}
                        handleSave={this.handleSave}
                    />
                </GridItem>
            </GridContainer>);
        }
        return (
            <Aux>
                <ReportToolbar
                    datasets = {this.state.datasets}
                    fields = {this.state.fields}
                    reportTitle = {this.state.reportTitle}
                    reportType = {this.state.reportType}
                    reportDescription = {this.state.reportDescription}
                    handleChange = {this.handleChange}
                    handleGraphChange = {this.handleGraphChange}
                    handleDatasetChange={this.handleDatasetChange}
                    handleFieldChange={this.handleFieldChange}
                    handleCancel={this.handleCancel}
                    handleLoad={this.handleLoad}
                    selectedYField = {this.state.selectedYField}
                    selectedDataset  ={this.state.selectedDataset}
                    selectedFields = {this.state.selectedFields}
                    selectedXField = {this.state.selectedXField}
                    selectedMeasureOperation = {this.state.selectedMeasureOperation}
                    selectedGroupBy = {this.state.selectedGroupBy}
                    handleGroupByChange = {this.handleGroupByChange }
                    handleMeasureOperation = {this.handleMeasureOperation}
                 />
                {report_data}

            </Aux>
        );
    }
}

const mapStateToProps = state => {
    return {
        reportData : state.report.reportData,
        options : state.report.options,
        auth_token : state.login.auth_token,
    }
};

const mapDispatchToProps = dispatch => {
    return {
        handleDataLoad : data => dispatch(handleDataLoad(data)),
        handleDefaultDataLoad : (data,type) => dispatch(handleDefaultDataLoad(data, type)),
        handleClearReportData : () => dispatch(handleClearReportData())
    }
}

export default connect(mapStateToProps, mapDispatchToProps)(withStyles(reportCreateStyle)(ReportCreate));
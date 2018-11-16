import React from 'react';
import Axios from 'axios';
import {withStyles} from '@material-ui/core/styles';
import ChartistGraph from 'react-chartist';

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

import {
    roundedLineChart,
    straightLinesChart,
    simpleBarChart,
    colouredLineChart,
    multipleBarsChart,
    colouredLinesChart,
    pieChart
  } from "variables/charts.jsx";

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
            report_data : {},
            reportOptions : {},
            reportListeners : {},
            filterChecked : false,
            selectedOperation : ''
        };
        this.ref = React.createRef();
        // this.resetFunc.bind(this);
    };

    // resetFunc = () => {}

    componentDidMount(){
        this.getDatasets();
    }

    getDatasets = () => {
        Axios.get('http://127.0.0.1:8000/api/datasets/')
        .then(res => {
            this.setState({ datasets : [...res.data]})
        }); 
    };

    handleDatasetChange = (e) => {
        console.log(e.currentTarget, typeof(e.target.value));
        e.persist();
        this.setState(prevState => {
            var i;
            let newFields = [];
            for(i=0; i < prevState.datasets.length; i++){
                console.log(e.target.value);
                if(prevState.datasets[i].name == e.target.value){
                    newFields = prevState.datasets[i].fields;
                    break;
                }
            }
            return { selectedDataset : e.target.value, fields : [...prevState.fields, ...newFields]}
        });
    };

    handleChange =  name => (e) => {
        console.log(e.currentTarget.value);
        this.setState({ [name] : e.currentTarget.value })
    }

    handleGraphChange = e => {
        const defaultData = this.getDefaultGraph(e.currentTarget.value);
        console.log(defaultData);
        this.setState({
            ...defaultData
        });
    }

    getDefaultGraph = name =>  {
        switch(name){
            case 'Bar':
                return {
                    reportType : name,
                    icon : (<BarChart/>),
                    report_data : multipleBarsChart.data,
                    reportOptions : multipleBarsChart.options,
                    reportListeners : multipleBarsChart.animation
                }
            default:
                return {}
        }
    }

    handleFieldChange  = (xField,yField) => {
        if(yField === null) {
            this.setState(prevState => ({
                selectedFields : [...prevState.selectedFields,xField],
                selectedXField : xField
            }));
        }
        else {
            this.setState(prevState => {
                if(prevState.selectedYField.indexOf(yField) === -1){
                    return {
                        selectedFields : [...prevState.selectedFields,yField],
                        selectedYField : [...prevState.selectedYField,yField]
                    }
                }
                else {
                    return {
                        selectedFields : [...prevState.selectedFields],
                        selectedYField : [...prevState.selectedYField]
                    }
                }
            });
        }
    };

    handleCancel = () => {
        this.setState({ fields : [],
            reportTitle : '',
            reportType: '',
            selectedFields : [],
            selectedXField : '',
            selectedYField : [],
            selectedDataset :  ''});
    }

    handleSave = () => {
        const postData = {
            url : 'http://127.0.0.1:8000/api/report_generate/',
            method : 'POST',
            data : JSON.stringify({
                'type' : this.state.reportType,
                'dataset' : this.state.selectedDataset,
                'report_title' : this.state.reportTitle,
                'report_description' : this.state.reportDescription,
                'options' : {
                    'X_field' : this.state.selectedXField,
                    'Y_field' : this.state.selectedYField
                }
            }),
            auth :  {
                username : 'sharabesh',
                password : 'shara1234'
            },
            headers : { 'Content-Type' : 'application/json'}
        };
        Axios(postData)
            .then(res => this.setState((prevState) => {
                const data = res.data.data;
                // const new_data = data.slice(1,-1);
                return { report_data : {...data} };
            }))
            .catch(err => console.error(err));
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

    render(){
        let report_data = null;
        const {classes} = this.props;
        if(Object.keys(this.state.report_data).length !== 0 && this.state.report_data.constructor === Object){
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
                    <CardBody>
                        <ChartistGraph 
                            data={this.state.report_data}
                            type={this.state.reportType}
                            options={this.state.reportOptions}
                            listener={this.state.reportListeners}
                        />
                    </CardBody>
                    <CardFooter stats>
                        <div className={classes.stats}>
                        <Danger>
                            <ZoomOutMap />
                        </Danger>
                        <a href="#pablo" onClick={e => {
                            console.log(resetFunc);
                            resetFunc && resetFunc();
                            }}>
                            Zoom
                        </a>
                        </div>
                    </CardFooter>
                </Card>
                </GridItem>
                <GridItem xs={12} sm={12} md={6}>
                    <FilterOptions 
                        yLen={this.state.report_data.series[0].length}
                        xLen={this.state.report_data.labels.length}
                        filterChecked = {this.state.filterChecked}
                        handleFilterToggle={this.handleFilterToggle}
                        handleFilterOptions={this.handleFilterOptions}
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
                    handleSave={this.handleSave}
                    selectedYField = {this.state.selectedYField}
                    selectedDataset  ={this.state.selectedDataset}
                    selectedFields = {this.state.selectedFields}
                    selectedXField = {this.state.selectedXField}
                    selectedYField = {this.state.selectedYField}
                 />
                {report_data}

            </Aux>
        );
    }
}

export default withStyles(reportCreateStyle)(ReportCreate);
import React from 'react';
import Axios from 'axios';
import ReportToolbar from "../../components/ReportToolbar/ReportToolbar";

import Aux from '../../hoc/aux/aux';

class Report extends React.Component{
    constructor(){
        super();
        this.state = {
            datasets : [],
            fields : [],
            reportTitle : '',
            selectedFields : [],
            selectedXField : '',
            selectedYField : '',
            selectedDataset :  '',
            report_data : ''
        };
    };

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

    handleTitleChange = (e) => {
        this.setState({ reportTitle : e.target.value })
    }

    handleFieldChange  = (xField,yField) => {
        if(yField === null) {
            this.setState(prevState => ({
                selectedFields : [...prevState.selectedFields,xField],
                selectedXField : xField
            }));
        }
        else {
            this.setState(prevState => ({
                selectedFields : [...prevState.selectedFields,xField],
                selectedYField : yField
            }));
        }
    };

    handleSave = () => {
        const postData = {
            url : 'http://127.0.0.1:8000/api/report_generate/',
            method : 'POST',
            data : JSON.stringify({
                'type' : 'hor_bar',
                'dataset' : this.state.selectedDataset,
                'report_title' : this.state.reportTitle,
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
                return { report_data : data };
            }))
            .catch(err => console.error(err));
    }

    render(){
        let report_data = (<div id='report_data'></div>);
        if(this.state.report_data !== ''){
            window.mpld3.draw_figure('report_data',this.state.report_data);
        }
        return (
            <Aux>
                <ReportToolbar
                    handleDatasetChange={this.handleDatasetChange}
                    handleFieldChange={this.handleFieldChange}
                    handleSave={this.handleSave}
                    datasets = {this.state.datasets}
                    fields = {this.state.fields}
                    reportTitle = {this.state.reportTitle}
                    handleTitleChange = {this.handleTitleChange}
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

export default Report
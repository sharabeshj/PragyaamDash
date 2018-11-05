import React from 'react';
import Axios from 'axios';
import ReportToolbar from "../ReportToolbar/ReportToolbar";

import Aux from '../../hoc/aux/aux';

class CreateReport extends React.Component{
    constructor(){
        super();
        this.state = {
            datasets : [],
            fields : [],
            reportTitle : '',
            reportType: '',
            selectedFields : [],
            selectedXField : '',
            selectedYField : '',
            selectedDataset :  '',
            report_data : {}
        };
        this.ref = React.createRef();
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

    handleChange =  name => (e) => {
        console.log(e.currentTarget.value);
        this.setState({ [name] : e.currentTarget.value })
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

    render(){
        let report_data = (<div id='report_data' ref = {this.ref}></div>);
        if(Object.keys(this.state.report_data).length !== 0 && this.state.report_data.constructor === Object){
            console.log(this.ref.current.firstChild);
            if(this.ref.current.firstChild !== null){
                this.ref.current.removeChild(this.ref.current.firstChild);
            }
            // document.getElementById('report_data').removeChild(document.getElementById('report_data').firstElementChild.nodeName)
            window.mpld3.draw_figure('report_data',this.state.report_data);
        }
        return (
            <Aux>
                <ReportToolbar
                    datasets = {this.state.datasets}
                    fields = {this.state.fields}
                    reportTitle = {this.state.reportTitle}
                    reportType = {this.state.reportType}
                    handleChange = {this.handleChange}
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

export default CreateReport
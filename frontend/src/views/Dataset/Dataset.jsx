import React,{Component} from 'react';
import PropTypes from 'prop-types';
import classNames from 'classnames';
import {
    DiagramWidget,
    DiagramEngine,
    DefaultLinkFactory,
    DefaultNodeFactory,
    DefaultNodeModel,
    DefaultPortModel
} from 'storm-react-diagrams';
import { connect } from 'react-redux';


import { withStyles } from '@material-ui/core/styles';
import Drawer from '@material-ui/core/Drawer';
import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemText from '@material-ui/core/ListItemText';
import ListItemSecondaryAction from '@material-ui/core/ListItemSecondaryAction';
import { Divider, Typography, Radio } from '../../../node_modules/@material-ui/core';

import OptionToolbar from '../../components/OptionToolbar/OptionToolbar';
import JoinToolbar from '../../components/JoinToolbar/JoinToobar';
import Aux from '../../hoc/aux/aux';
import SaveOption from '../../components/SaveOption/SaveOption';
import CustomDropdown from '../../components/CustomDropdown/CustomDropdown';

import datasetStyle from '../../assets/jss/frontend/views/dataset';
import '../../assets/css/srd.css';

import { saveDataset,tableAdd } from '../../store/Actions/ActionCreator';
import Axios from 'axios';

class Dataset extends Component {
    constructor(props){
        super(props);
        this.state = {
            workSpace : [],
            selectedWorkSpace : '',
            workSheet : [],
            selectedWorkSheet : [],
            worksheetData : [],
            joinData : [],
            name : ''
        };
    }

    componentWillMount(){
        this.engine = new DiagramEngine();

        this.engine.registerNodeFactory(new DefaultNodeFactory());
        this.engine.registerLinkFactory(new DefaultLinkFactory());
    }

    componentDidMount(){
        if(this.props.login.token !== '') {
            const postData = {
                url : 'http://pragyaamfrontend.mysnippt.com/api/workspace/view',
                method : 'POST',
                data : JSON.stringify({ organization_id : this.props.login.orgId }),
                headers : {
                    'Authorization' : `Bearer ${this.props.login.token}`,
                    'Content-Type' : 'application/json'
                }
            };
            Axios(postData).then( res => this.setState({ workSpace : res.data.data })).catch(e => console.error(e));
        }
    }

    componentDidUpdate(prevProps,prevState){
        if(this.props.dataset.fields){
            if(this.props.dataset.fields.length !== prevProps.dataset.fields.length){
                this.props.dataset.fields.forEach(field =>  {
                    Object.entries(this.engine.getDiagramModel().getNodes()).forEach(
                        ([key,value]) => {
                            if(value.name === field.worksheet){
                                Object.entries(this.engine.getDiagramModel().getNode(key).getPorts()).forEach(
                                    ([name,val]) => {
                                        if(!(val.name === 'in-1' || val === 'out-1')) {
                                        if (this.props.dataset.fields.findIndex(x => x.name === val.name )=== -1){
                                            this.engine.getDiagramModel().getNode(key).removePort(val);
                                        }
                                    }
                                    }
                                );
                                this.engine.getDiagramModel().getNode(key).addPort(new DefaultPortModel(false,`${field.name}`,field.name));
                                this.forceUpdate();
                            }
                        }
                    )
                });
            }
        }
        
    }

    // handleToggle = value  => {
    //     const { selectedWorkSheet,workSheet } = this.state;
    //     const currentIndex = selectedWorkSheet.indexOf(workSheet[value]);
    //     const newSelectedWorkSheet =  [...selectedWorkSheet]

    //     if(currentIndex === -1){
    //         newSelectedWorkSheet.push(workSheet[value]);
    //     } 
    //     else {
    //         newSelectedWorkSheet.splice(currentIndex,1)
    //     }

    //     this.setState({
    //         selectedWorkSheet : newSelectedWorkSheet
    //     })
    // }

    getWorksheets = (workspace_id,event) => {
        const postData = {
            url : 'http://pragyaamfrontend.mysnippt.com/api/worksheet/view',
            method : 'POST',
            data : JSON.stringify({
                organization_id : this.props.login.orgId,
                workspace_id : workspace_id
            }),
            headers : {
                'Authorization' : `Bearer ${this.props.login.token}`,
                'Content-Type' : 'application/json'
            }
        };
        Axios(postData) .then(res => this.setState({ workSheet : res.data.data })) .catch(e => console.error(e));
    }

    getWorksheetData = (worksheet) => {
        this.props.tableAdd(worksheet.name);
        const postData = {
            url : `http://pragyaamfrontend.mysnippt.com/api/entrypage`,
            method : 'POST',
            data : JSON.stringify({
                organization_id : this.props.login.orgId,
                worksheet_id : worksheet.key
            }),
            headers : {
                'Authorization' : `Bearer ${this.props.login.token}`,
                'Content-Type' : 'application/json'
            }
        }
        Axios(postData) .then(res => this.setState(prevState => {
            const worksheetData = {
                worksheet_name : worksheet.name,
                data : [...res.data.data]
            };
            return {worksheetData : [...prevState.worksheetData,worksheetData]};
        })) 
        .catch(e => console.error(e));
        
    }

    handleSubmit = (event) =>  {
        let allJoinData = [];
        Object.entries(this.engine.getDiagramModel().getNodes()).forEach(
            ([key,value]) => {
                if(value.name === "Inner-Join" || value.name === "Right-Join" || value.name === "Left-Join" || value.name === "Outer-Join"){
                    Object.entries(this.engine.getDiagramModel().getNode(key).getPorts()).forEach(
                        ([name,val]) => {
                            if(val.in){
                                Object.entries(this.engine.getDiagramModel().getNode(key).getPort(name).getLinks()).forEach(
                                    ([linkKey,linkVal]) => {
                                        let JoinData = {
                                            type : value.name,
                                            field : linkVal.sourcePort.name,
                                            worksheet_1 : linkVal.sourcePort.parent.name
                                        }
                                        Object.entries(this.engine.getDiagramModel().getNode(key).getPorts()).forEach(
                                            ([n,v]) => {
                                                if(!v.in){
                                                    Object.entries(this.engine.getDiagramModel().getNode(key).getPort(n).getLinks()).forEach(
                                                        ([oLinkName,oLinkVal]) => { 
                                                            JoinData.worksheet_2 = oLinkVal.targetPort.parent.name;
                                                            allJoinData = [...new Set([...allJoinData,JoinData])];
                                                        }
                                                    );
                                                }
                                            }
                                        );
                                    }
                                );
                            }
                        }
                    );
                }
            }
        );
        this.props.saveDataset(this.state.name,allJoinData);
    }

    handleChange = e => {
        this.setState({ name : e.target.value })
    }
    
    render(){
        const {classes} = this.props;

        let list = null;

        let optionToolbar = null;

        let joinToolbar = null;

        let saveOption = null;

        let workspaceOption = null;

        if(this.state.workSpace.length > 0) workspaceOption = (<CustomDropdown 
            buttonText = "Select Workspace"
            dropdownHeader = "Select Workspace"
            dropdownList = {this.state.workSpace.map(workspace => {
                return <div key = {workspace.workspace_id} onClick = {e => this.getWorksheets(workspace.workspace_id,e)}>{workspace.workspace_name}</div>
            })}
         />);

        if(Object.keys(this.engine.getDiagramModel().getNodes()).length >= 2){
            joinToolbar = (<JoinToolbar />);
        }

        if(this.state.workSheet.length > 0){
            list = this.state.workSheet.map((worksheet) => {
               return ( <div key = {worksheet.worksheet_id}
                        draggable = {true}
                        onDragStart = { event => {
                            event.dataTransfer.setData('worksheet',JSON.stringify({ name : worksheet.worksheet_name, key : worksheet.worksheet_id }));
                        }}
                    ><List>
                    <ListItem dense button>
                    <ListItemText primary = {worksheet.worksheet_name}/>
                    <ListItemSecondaryAction>
                        <Radio
                            checked  = {this.state.selectedWorkSheet.indexOf(worksheet.worksheet_id) !== -1}
                            value = {worksheet.worksheet_name}
                            aria-label = {worksheet.worksheet_name}
                            name = {worksheet.worksheet_name}
                            classes = {{
                                root : classes.radio,
                                checked : classes.radio_checked,
                            }}
                        /> 
                    </ListItemSecondaryAction>
                </ListItem></List></div>)
            })
        }

        if(this.state.worksheetData.length > 0){
            console.log('hi');
            optionToolbar = (
                    <OptionToolbar worksheetData = {this.state.worksheetData}/>
                 );

            saveOption = (<SaveOption 
                handleSubmit = {this.handleSubmit}
                handleChange = {this.handleChange}
                content = {this.state.name}
                />)
        }

        const drawer = (
            <Aux>
                <Drawer
                variant = "permanent"
                classes = {{
                    paper : classes.drawerPaper
                }}
                anchor = "left"
            >
                 <div className = {classes.toolbar}>
                    {"DATASET CREATION"}
                 </div>
                 <Divider />
                 {workspaceOption}
                 <Divider/>
                 <List>
                 {list}
                 </List>
                 <Divider />
                 {joinToolbar}
                 <Divider />
                 {optionToolbar}
            </Drawer>
            </Aux>
        );
        return (
            <div className = {classes.root}>
                <div className = {classes.appFrame}>
                {drawer}
                <div className = {classes.content}>
                    {saveOption}
                    <div
                        className = "diagram-layer"
                        onDrop = { event => {
                            event.preventDefault();
                            let data = JSON.parse(event.dataTransfer.getData('worksheet'));
                            let worksheet = new DefaultNodeModel(data.name);
                            worksheet.addPort(new DefaultPortModel(true,'in-1','X'));
                            worksheet.addPort(new DefaultPortModel(false,'out-1','O'));
                            let points = this.engine.getRelativeMousePoint(event);
                            worksheet.x = points.x;
                            worksheet.y = points.y;
                            this.engine.getDiagramModel().addNode(worksheet);
                            this.forceUpdate ();
                            if(data.name !== 'Inner-Join' && data.name !== 'Left-Join' && data.name !== 'Right-Join' && data.name !== 'Outer-Join')
                            this.getWorksheetData(data);
                        
                        }}
                        onDragOver = { event => {
                            event.preventDefault();
                        }}
                    >
                        <DiagramWidget diagramEngine= {this.engine}/>
                    </div>
                </div>
                </div>
            </div>
        );
    }
}

Dataset.propTypes = {
    classes : PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
    dataset : state.dataset,
    login : state.login
});

const mapDispatchToProps = dispatch => {
    return {
        saveDataset : (name,joinData) => dispatch(saveDataset(name,joinData)),
        tableAdd : (table) => dispatch(tableAdd(table))
    }
}

export default connect(mapStateToProps,mapDispatchToProps)(withStyles(datasetStyle)(Dataset));
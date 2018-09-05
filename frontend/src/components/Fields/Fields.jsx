import React from 'react';
import Proptypes from 'prop-types';
import { connect } from 'react-redux';

import { withStyles } from '@material-ui/core/styles';
import Checkbox from '@material-ui/core/Checkbox';
import Tooltip from '@material-ui/core/Tooltip';
import IconButton from '@material-ui/core/IconButton';
import Table from '@material-ui/core/Table';
import TableRow from '@material-ui/core/TableRow';
import TableBody from '@material-ui/core/TableBody';
import TableCell from '@material-ui/core/TableCell';

import AddCircle from '@material-ui/icons/AddCircle';
import Close from '@material-ui/icons/Close';
import Check from '@material-ui/icons/Check';

import fieldsStyle from '../../assets/jss/frontend/components/fieldsStyle';

import { fieldAdd } from '../../store/Actions/ActionCreator';

class Fields extends React.Component{
    
    constructor(props){
        super(props);
        this.state = {
            selectedFields : this.props.selectedFields
        }
    }

    handleToggle = value => {
        const { selectedFields } = this.state;
        const currentIndex = selectedFields.indexOf(value);
        const newSelectedfields = [...selectedFields];

        if(currentIndex === -1) {
            newSelectedfields.push(value);
        }
        else {
            newSelectedfields.splice(currentIndex,1);
        }

        this.setState(() => {
            const fields = newSelectedfields.map(field => {
                for(let item of this.props.fieldData){
                    if(item.column == field){
                        let data = {
                            name : item.column,
                            worksheet : this.props.worksheet_name
                        }
                        switch(item.type){
                            case 'text':
                                return {
                                    ...data,
                                    type : 'CharField',
                                    settings : [{
                                        name : 'max_length',
                                        value : 20
                                    }]
                                };
                            case 'number':
                                return {
                                    ...data,
                                    type : 'IntegerField',
                                    settings : []
                                };
                            case 'decimal':
                                return {
                                    ...data,
                                    type : 'FloatField',
                                    settings : []
                                };
                            case 'single':
                                return {
                                    ...data,
                                    type : 'IntegerField',
                                    settings : []
                                };
                            case 'date':
                                return {
                                    ...data,
                                    type : 'IntegerField',
                                    settings : []
                                };
                        }
                    }
                }
            });
            
            this.props.fieldAdd(fields);
            return { selectedFields : newSelectedfields };
        });
    };

    render(){
        const { classes, fieldData } = this.props;

        return (
            <Table className = {classes.table}>
                <TableBody>
                    {fieldData.map((field,key) => (
                        <TableRow key = {key} className = {classes.tableRow}>
                            <TableCell className = {classes.tableCell}>
                                <Checkbox 
                                    checked = {this.state.selectedFields.indexOf(field.column) !== -1}
                                    tabIndex={-1}
                                    onClick = {() => this.handleToggle(field.column)}
                                    checkedIcon={<Check className = {classes.checkedIcon}/>}
                                    icon = {<Check className = {classes.uncheckedIcon}/>}
                                    classes = {{
                                        checked : classes.checked
                                    }}
                                />
                            </TableCell>
                            <TableCell className = {classes.tableCell}>
                                {field.column}
                            </TableCell>
                            <TableCell className = {classes.tableActions}>
                                <Tooltip
                                    id = "tooltip-top"
                                    title = "Backward-Link"
                                    placement = "top"
                                    classes = {{ tooltip : classes.tooltip }}
                                >
                                    <IconButton
                                        aria-label = "B-L"
                                        className = {classes.tableActionsButton}
                                    >
                                        <Close 
                                            className = {classes.tableActionsButton + " " + classes.bL}
                                        />
                                    </IconButton>
                                </Tooltip>
                                <Tooltip
                                    id = "tooltip-top-start"
                                    title = "Forward-Link"
                                    placement = "top"
                                    classes = {{tooltip : classes.tooltip}}
                                >
                                    <IconButton
                                        aria-label = "F-L"
                                        className = {classes.tableActionsButton}
                                    >
                                        <AddCircle 
                                            className = {
                                                classes.tableActionsButton + " " + classes.fL
                                            }
                                        />
                                    </IconButton>
                                </Tooltip>
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        );
    }
}

Fields.propTypes = {
    classes : Proptypes.object.isRequired,
    fields : Proptypes.arrayOf(Proptypes.string)
};

const mapStateToProps = state => {
    return {
        selectedFields : state.dataset.fields
    }
};

const mapDispatchToProps = dispatch => {
    return {
        fieldAdd : fields => dispatch(fieldAdd(fields))
    }
}

export default connect(mapStateToProps,mapDispatchToProps)(withStyles(fieldsStyle)(Fields));

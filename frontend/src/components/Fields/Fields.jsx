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

    handleToggle = (value,e) => {
        const currentIndex = this.props.selectedFields.map(field => field.name).indexOf(value.column_aliases);
        const newSelectedfields = [...this.props.selectedFields];

        if(currentIndex === -1) {
            console.log('came in ');
            let data = {
                name : value.column_aliases,
                worksheet : this.props.worksheet_name
            }
            switch(value.type){
                case 'text':
                    data = {
                        ...data,
                        type : 'CharField',
                        settings : [{
                            name : 'max_length',
                            value : 20
                        }]
                    };
                    break;
                case 'number':
                    data =  {
                        ...data,
                        type : 'IntegerField',
                        settings : []
                    };
                    break;                                    
                case 'decimal':
                    data = {
                        ...data,
                        type : 'FloatField',
                        settings : []
                    };
                    break;
                case 'single':
                    data = {
                        ...data,
                        type : 'IntegerField',
                        settings : []
                    };
                    break;
                case 'date':
                    data = {
                        ...data,
                        type : 'IntegerField',
                        settings : []
                    };
                    break;
                default:
                    data = {
                        ...data
                    };
                    break;
            }
            newSelectedfields.push(data);
        }
        else {
            newSelectedfields.splice(currentIndex,1);
        }
            
        this.props.fieldAdd(newSelectedfields);
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
                                    checked = {this.props.selectedFields.map(val => val.name).indexOf(field.column_aliases) !== -1}
                                    tabIndex={-1}
                                    onClick = {(e) => this.handleToggle(field,e)}
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

import React from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import classnames from 'classnames';
import ExpansionPanel from '@material-ui/core/ExpansionPanel';
import ExpansionPanelDetails from '@material-ui/core/ExpansionPanelDetails';
import ExpansionPanelSummary from '@material-ui/core/ExpansionPanelSummary';
import ExpansionPanelActions from '@material-ui/core/ExpansionPanelActions';
import Typography from '@material-ui/core/Typography';
import ExpandMoreIcon from '@material-ui/icons/ExpandMore';
import BarChart from '@material-ui/icons/BarChart';
import ShowChart from '@material-ui/icons/ShowChart';
import Sort from '@material-ui/icons/Sort';
import ViewList from '@material-ui/icons/ViewList';
import ViewModule from '@material-ui/icons/ViewModule';
import PieChart from '@material-ui/icons/PieChart';
import DonutLarge from '@material-ui/icons/DonutLarge';
import ScatterPlot from '@material-ui/icons/ScatterPlot';
import Chip from '@material-ui/core/Chip';
import Button from '@material-ui/core/Button';
import TextField from '@material-ui/core/TextField';
import Divider from '@material-ui/core/Divider';

import reportToolbarStyles from '../../assets/jss/frontend/components/reportToolbarStyles';

function ReportToolbar(props) {
    const { classes } = props;
    const newSelectedYOptions  = (<TextField
        id={"select y field"}
        select
        placeholder={"Select new Y field"}
        value={''}
        label={"Select Y Field"}
        className={classes.textField}
        onChange={(e) => props.handleFieldChange(null,e.currentTarget.value)}
        SelectProps={{
            MenuProps : {
                className : classes.menu,
            },
        }}
        helperText={"Please select your y field"}
        margin = "normal"
        variant={"outlined"}
    >
        {props.fields && props.fields.map(field => (
            <option disabled={props.selectedFields.indexOf(field)!=-1} value={field} key={field}>
                {field}
            </option>
        ))}
    </TextField>);
    let selectedYOptions = null;
    if(props.selectedYField && props.selectedYField.length > 0){
        selectedYOptions = props.selectedYField.map(yField => (
            <TextField
                            id={"select y field"}
                            key={yField}
                            select
                            label={"Select Y Field"}
                            className={classes.textField}
                            value={yField}
                            onChange={(e) => props.handleFieldChange(null,e.currentTarget.value)}
                            SelectProps={{
                                MenuProps : {
                                    className : classes.menu,
                                },
                            }}
                            helperText={"Please select your y field"}
                            margin = "normal"
                            variant={"outlined"}
                        >
                            {props.fields && props.fields.map(field => (
                                <option disabled={props.selectedFields.indexOf(field)!=-1} value={field} key={field}>
                                    {field}
                                </option>
                            ))}
                        </TextField>
        ));
        
    }
    
    return (
        <div className={classes.root}>
            <ExpansionPanel defaultExpanded>
                <ExpansionPanelSummary expandIcon={<ExpandMoreIcon/>}>
                    <div className={classes.column}>
                        <Typography className={classes.heading}>
                            Report Toolbar
                        </Typography>
                    </div>
                    <div className={classes.column}>
                        <Typography className={classes.secondary}>
                            Select options
                        </Typography>
                    </div>
                </ExpansionPanelSummary>
                <ExpansionPanelDetails className={classes.details}>
                    <div className={classes.column}>
                        <Button variant={"fab"} aria-label={"Hor_bar"} className={classes.HorBarButton} value = 'hor_bar' onClick = {props.handleChange('reportType')} disabled = {props.reportType === '' ? false : true}>
                            <Sort/>
                        </Button>
                        <Button variant={"fab"} aria-label={"Line_graph"} className={classes.HorBarButton} value = 'line_graph' onClick = {props.handleChange('reportType')} disabled = {props.reportType === '' ? false : true}>
                            <ShowChart/>
                        </Button>
                        <Button variant={"fab"} aria-label={"bar_graph"} className={classes.HorBarButton} value = 'bar_graph' onClick={props.handleChange('reportType')} disabled = {props.reportType === '' ? false : true}>
                            <BarChart/>
                        </Button>
                        <Button variant={"fab"} aria-label={"stacked_hor_bar"} className={classes.HorBarButton} value='stacked_hor_bar' onClick={props.handleChange('reportType')} disabled = {props.reportType === '' ? false : true}> 
                            <ViewList />
                        </Button>
                        <Button variant={"fab"} aria-label={"stacked_bar_graph"} className={classes.HorBarButton} value='stacked_bar_graph' onClick={props.handleChange('reportType')} disabled = {props.reportType === '' ? false : true}> 
                            <ViewModule/>
                        </Button>
                        <Button variant={"fab"} aria-label={"pie_graph"} className={classes.HorBarButton} value='pie_graph' onClick={props.handleChange('reportType')} disabled = {props.reportType === '' ? false : true}> 
                            <PieChart/>
                        </Button>
                        <Button variant={"fab"} aria-label={"donut_graph"} className={classes.HorBarButton} value='donut_graph' onClick={props.handleChange('reportType')} disabled = {props.reportType === '' ? false : true}> 
                            <DonutLarge/>
                        </Button>
                        <Button variant={"fab"} aria-label={"scatter_graph"} className={classes.HorBarButton} value='scatter_graph' onClick={props.handleChange('reportType')} disabled = {props.reportType === '' ? false : true}> 
                            <ScatterPlot/>
                        </Button>
                    </div>
                    <div className={classes.column}>
                        <TextField
                            id="reportTitle"
                            label="Report Title"
                            className = {classes.textField}
                            value={props.reportTitle}
                            onChange={props.handleChange('reportTitle')}
                            margin="normal"
                            variant="outlined"
                        />  
                        <TextField
                            id={"select dataset"}
                            select
                            label={"Select dataset"}
                            className={classes.textField}
                            value={props.selectedDataset}
                            onChange={(e) => props.handleDatasetChange(e)}
                            SelectProps={{
                                MenuProps : {
                                    className : classes.menu,
                                },
                            }}
                            helperText={"Please select your dataset"}
                            margin = "normal"
                            variant={"outlined"}
                        >
                            {props.datasets.map(option => (
                                <option key={String(props.datasets.indexOf(option))} value={option.name} data-fields = {`${option.fields}`}>
                                    {option.name}
                                </option>
                            ))}
                        </TextField>
                        <TextField
                            id={"select x field"}
                            select
                            label={"Select X Field"}
                            className={classes.textField}
                            value={props.selectedXField}
                            onChange={(e) => props.handleFieldChange(e.currentTarget.value,null)}
                            SelectProps={{
                                MenuProps : {
                                    className : classes.menu,
                                },
                            }}
                            helperText={"Please select your x field"}
                            margin = "normal"
                            variant={"outlined"}
                        >
                            {props.fields && props.fields.map(field => (
                                <option disabled={props.selectedFields.indexOf(field)!=-1} value={field} key={field}>
                                    {field}
                                </option>
                            ))}
                        </TextField>
                        {selectedYOptions}
                        {newSelectedYOptions}
                    </div>
                </ExpansionPanelDetails>
                <Divider/>
                <ExpansionPanelActions>
                    <Button size={"small"} onClick={props.handleCancel}>Cancel</Button>
                    <Button size={"small"} color={"primary"} onClick={props.handleSave}>Save</Button>
                </ExpansionPanelActions>
            </ExpansionPanel>
        </div>
        );
}

ReportToolbar.propTypes = {
    classes : PropTypes.object.isRequired,
};

export default withStyles(reportToolbarStyles)(ReportToolbar);

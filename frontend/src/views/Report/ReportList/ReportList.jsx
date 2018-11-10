import React from 'react';
import Axios from 'axios';
import PropTypes from 'prop-types';
import classNames from 'classnames';
import {Link} from 'react-router-dom';

import Button from '@material-ui/core/Button';
import Card from '@material-ui/core/Card';
import CardActions from '@material-ui/core/CardActions';
import CardContent from '@material-ui/core/CardContent';
import CardMedia from '@material-ui/core/CardMedia';
import CssBaseline from '@material-ui/core/CssBaseline';
import Grid from '@material-ui/core/Grid';
import Typography from '@material-ui/core/Typography';
import { withStyles } from '@material-ui/core/styles';
import Add from '@material-ui/icons/Add';

import CustomButton from '../../../components/CustomButtons/Button';

import reportListStyles from '../../../assets/jss/frontend/components/ReportList';


class ReportList extends React.Component{
    constructor(props){
        super(props);
        this.state = {
            reportDataList : []
        };
    }

    componentDidMount(){
        const data = {
            url : 'http://127.0.0.1:8000/api/reports/',
            method : 'GET',
            auth : {
                username : 'sharabesh',
                password : 'shara1234'
            }
        };
        Axios(data)
        .then(res => {
            this.setState({ reportDataList : res.data });
            this.loadReportdata();
        })
        .catch(e => console.error(e));
    }

    loadReportdata = () => {
        this.state.reportDataList.forEach(report => {
            window.mpld3.draw_figure(String(this.state.reportDataList.indexOf(report)),report.data)
        });
    }

    render(){
        const { classes } = this.props;

        return (
            <React.Fragment>
                <CssBaseline />
                <main>
                    <div className={classes.heroUnit}>
                        <div className={classes.heroContent}>
                            <Typography component="h1" variant="h2" align="center" color = "textPrimary" gutterBottom>
                                Report Customization
                            </Typography>
                            <Typography variant="h6" align="center" color="textSecondary" paragraph> 
                                Collection of reports generated by various users - Customizable and save to dashboard 
                            </Typography>
                            <div className={classes.heroButtons}>
                                <Grid container spacing={16} justify="center">
                                    <Grid item>
                                    <Link to='/report/reportCreate'>
                                    <CustomButton size = 'md' color="primary">
                                            Create Report<Add/>
                                        </CustomButton>
                                    </Link>
                                        
                                    </Grid>
                                    <Grid item>
                                        <Button variant="outlined" color="success">
                                            <Link to="/dashboard">View dashboard</Link>
                                        </Button>
                                    </Grid>
                                </Grid>
                            </div>
                        </div>
                    </div>
                    <div className={classNames(classes.layout, classes.cardGrid)}>
                        <Grid container spacing={40}>
                            {this.state.reportDataList.map(report => (
                                <Grid item key={report.data} sm={6} md={4} lg={3}>
                                    <Card className={classes.card}>
                                        <CardMedia 
                                            className={classes.cardMedia}
                                            id={String(this.state.reportDataList.indexOf(report))}
                                        />
                                        <CardContent className={classes.card}>
                                            <Typography gutterBottom variant="h5" component="h2">
                                                {report.title}
                                            </Typography>
                                            <Typography>
                                                {report.description}
                                            </Typography>
                                        </CardContent>
                                        <CardActions>
                                            <Button size="small" color="success">
                                                Add
                                            </Button>
                                            <Button size="small" color="success">
                                                Edit
                                            </Button>
                                        </CardActions>
                                    </Card>
                                </Grid>
                            ))}
                        </Grid>
                    </div>
                </main>
            </React.Fragment>
        );
    }
}

ReportList.propTypes = {
    classes : PropTypes.object.isRequired,
};

export default withStyles(reportListStyles)(ReportList);
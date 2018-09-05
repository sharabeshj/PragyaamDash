import React from 'react';
import { withStyles } from '@material-ui/core/styles';

import Fields from '../Fields/Fields';
import CustomTabs from '../CustomTabs/CustomTabs';
import Icon from '../../variables/icons';

import optionToolbarStyle from '../../assets/jss/frontend/components/optionToolbarStyle';

class OptionToolbar extends React.Component{
    state = {
        worksheetData : []
    };

    static getDerivedStateFromProps(nextProps,prevState){
        if(nextProps.worksheetData && nextProps.worksheetData!==prevState.worksheetData){
            return { worksheetData : nextProps.worksheetData };
        }
        console.log('hi')
        return null;
    };

    render(){
        const { classes } = this.props;
        const worksheets = this.state.worksheetData.map((worksheet,key) => {
           return {
               tabName : worksheet.worksheet_name,
               tabIcon : Icon(key%10),
               tabContent : (
                   <Fields 
                        fields = {worksheet.columnData.columns}
                        fieldData = { worksheet.columnData.data }
                        worksheet_name = {worksheet.worksheet_name}
                   />
               )
           }
       });
    //    console.log(this.state.worksheetData);
       return(
           <div className = {classes.toolbar}>
                 <CustomTabs 
                    title = "Worksheets:"
                    headerColor = "success"
                    tabs = {worksheets}
                />
           </div>
       ) 
    }
}

export default withStyles(optionToolbarStyle)(OptionToolbar);
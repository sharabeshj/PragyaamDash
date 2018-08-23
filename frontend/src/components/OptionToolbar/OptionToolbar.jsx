import React from 'react';

import Fields from '../Fields/Fields';
import CustomTabs from '../CustomTabs/CustomTabs';
import Icon from '../../variables/icons';

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
       const worksheets = this.state.worksheetData.map((worksheet,key) => {
           return {
               tabName : worksheet.worksheet_name,
               tabIcon : Icon(key%10),
               tabContent : (
                   <Fields 
                        fields = {worksheet.columnData.columns}
                        worksheet_name = {worksheet.worksheet_name}
                   />
               )
           }
       });
    //    console.log(this.state.worksheetData);
       return(
           <CustomTabs 
            title = "Worksheets:"
            headerColor = "success"
            tabs = {worksheets}
           />
       ) 
    }
}

export default OptionToolbar;
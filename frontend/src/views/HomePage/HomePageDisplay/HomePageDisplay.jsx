import React from 'react';
import Chartist from 'chartist';
import Axios from 'axios';

class HomePageDisplay extends React.Component{
    constructor(props){
        super(props);
        this.state = {
            dashboardDisplayData : []
        };
    }

    componentDidMount(){
        const postData = {
            method : 'GET',
            url : 'http://127.0.0.1:8000/api/dashbaordDisplay/',
            auth : {
                username : 'sharabesh',
                password : 'shara1234'
            }
        };

        Axios(postData)
        .then( res => this.setState({ dashboardDisplayData : res.data }))
        .catch(e => console.error(e));
    }

    render(){
        let dashboardDisplayData = null;

        if(this.state.dashboardDisplayData.length > 0){
            dashboardDisplayData = this.state.dashboardDisplayData.map(data => (
                <div>hi</div>
            ))
        }

        return(
            <div>
            {dashboardDisplayData}
            </div>
        )
    }
};

export default HomePageDisplay;
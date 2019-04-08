import React from 'react';
import { connect } from 'react-redux';

class Logout extends React.Component {
    componentDidMount(){

    }
    render(){
        return(
            <div>
                You are logged out!
            </div>
        )
    }
}

const mapDispatchToProps = dispatch => {
    return {
        logout: dispatch()
    }
}

export default connect(null, mapDispatchToProps)(Logout);
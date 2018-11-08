import React from 'react';
import { Switch, Route } from 'react-router-dom';

import aux from '../../hoc/aux/aux';
import reportRoutes from '../../routes/report';

const switchRoutes = (
    <Switch>
        {reportRoutes.map((prop,key) => {
            return <Route path={prop.path} component = {prop.component} key = {key}/>
        })}
    </Switch>
);

class Report extends React.Component {
    render(){
        return (
            <aux>
                {switchRoutes}
            </aux>
        );
    }
};

export default Report;
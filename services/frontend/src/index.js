import React from 'react';
import ReactDOM from 'react-dom';
import { createBrowserHistory } from 'history';
import { Router, Route, Switch } from 'react-router-dom';
import registerServiceWorker from './registerServiceWorker';
import { Provider } from 'react-redux';
import ConfigureStore from './store/ConfigureStore';

import './assets/scss/frontend.css';
import './assets/css/tooltip.css';
import './assets/css/zoom.css';

import indexRoutes from './routes/index';


const hist = createBrowserHistory();

const store = ConfigureStore();

ReactDOM.render(<Provider store = { store }><Router history = {hist}>
    <Switch>
        {indexRoutes.map((prop, key) => {
            return <Route path = {prop.path} component = {prop.component} key = {key}/>
        })}
    </Switch>
</Router></Provider>, document.getElementById('root'));
registerServiceWorker();

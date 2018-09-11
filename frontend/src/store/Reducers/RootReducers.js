import { combineReducers } from 'redux';

import DatasetHandler from './DatasetReducers';
import LoginHandler from './LoginReducers';

const RootReducers = combineReducers({
    dataset : DatasetHandler,
    login : LoginHandler
});

export default RootReducers;
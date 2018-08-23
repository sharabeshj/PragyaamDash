import { combineReducers } from 'redux';

import DatasetHandler from './DatasetReducers';

const RootReducers = combineReducers({
    dataset : DatasetHandler
});

export default RootReducers;
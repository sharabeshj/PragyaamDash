import React from 'react';

import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemText from '@material-ui/core/ListItemText';

import JoinOptions from '../../variables/joinOptions';

const JoinToolbar = () => {
    return JoinOptions.map((option,key) => (
        <div key = {key}
            draggable = {true}
            onDragStart = { event => {
                event.dataTransfer.setData('worksheet',JSON.stringify({ name : option }))
            }}
        >
            <List>
                <ListItem dense button>
                    <ListItemText primary = {option}/>
                </ListItem>
            </List>
        </div>
    ));
}

export default JoinToolbar;
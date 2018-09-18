import {
    drawerWidth,
} from '../../frontend';
import green from '@material-ui/core/colors/green';

const datasetStyle = theme => ({
    root : {
        flexGrow : 1,
    },
    appFrame : {
        height : '100%',
        zIndex : 1,
        overflow : 'auto',
        position : 'relative',
        display : 'flex',
        width : '100%',
    },
    drawerPaper : {
        position : 'relative',
        width : drawerWidth,
        overflow : 'auto'
    },
    toolbar : theme.mixins.toolbar,
    content: {
        flexGrow : 1,
        width : '100%',
        backgroundColor : theme.palette.background.default,
        padding : theme.spacing.unit * 3,
    },
    radio : {
        color : green[600],
        '&$checked' : {
            color : green[500],
        },
    },
    radio_checked : {},
    listStyle : {
        zIndex : -1
    }
});

export default datasetStyle;
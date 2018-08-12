import {
    drawerWidth,
} from '../../frontend';

const datasetStyle = theme => ({
    root : {
        flexGrow : 1,
    },
    appFrame : {
        height : '100%',
        zIndex : 1,
        overflow : 'hidden',
        position : 'relative',
        display : 'flex',
        width : '100%',
    },
    drawerPaper : {
        position : 'relative',
        width : drawerWidth,
    },
    toolbar : theme.mixins.toolbar,
    content: {
        flexGrow : 1,
        backgroundColor : theme.palette.background.default,
        padding : theme.spacing.unit * 3,
    },
});

export default datasetStyle;
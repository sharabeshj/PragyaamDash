import customSelectStyle from "../customSelectStyle";
import {cardTitle} from '../../frontend';

const reportToolbarStyles = theme => ({
    root: {
        width: '100%',
    },
    heading: {
        fontSize: theme.typography.pxToRem(15),
    },
    secondaryHeading: {
        fontSize: theme.typography.pxToRem(15),
            color: theme.palette.text.secondary,
    },
    icon: {
        verticalAlign: 'bottom',
            height: 20,
            width: 20,
    },
    details: {
        alignItems: 'center',
    },
    column: {
        flexBasis: '33.33%',
    },
    helper: {
        borderLeft: `2px solid ${theme.palette.divider}`,
            padding: `${theme.spacing.unit}px ${theme.spacing.unit * 2}px`,
    },
    link: {
        color: theme.palette.primary.main,
            textDecoration: 'none',
            '&:hover': {
            textDecoration: 'underline',
        },
    },
    textField: {
        marginLeft: theme.spacing.unit,
        marginRight: theme.spacing.unit,
    },
    dense: {
        marginTop: 16,
    },
    menu: {
        width: 200,
    },
    ...customSelectStyle,
    cardTitle,
    cardIconTitle: {
        ...cardTitle,
        marginTop: "15px",
        marginBottom: "0px"
    },
    label: {
        cursor: "pointer",
        paddingLeft: "0",
        color: "rgba(0, 0, 0, 0.26)",
        fontSize: "14px",
        lineHeight: "1.428571429",
        fontWeight: "400",
        display: "inline-flex"
    },
    mrAuto: {
        marginRight: "auto"
    },
    mlAuto: {
        marginLeft: "auto"
    },
    
});

export default reportToolbarStyles;
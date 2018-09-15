import React from 'react';

import { withStyles } from '@material-ui/core/styles';
import Dialog from '@material-ui/core/Dialog';
import DialogContent from '@material-ui/core/DialogActions';
import Close from '@material-ui/icons/Close';
import IconButton from '@material-ui/core/IconButton'
import DialogTitle from '@material-ui/core/DialogTitle';

import Table from '../Table/Table';
import Card from '../Card/Card';
import CardHeader from '../Card/CardHeader';
import CardBody from '../Card/CardBody'; 

import tableModalStyle from '../../assets/jss/frontend/components/tableModalStyle';

const TableModal = props => {
    const {classes} = props;
    return (
        <Dialog
            classes = {{
                root : classes.center,
                paper : classes.modal
            }}
            open = {props.modalOpen}
            TransitionComponent = {props.transition}
            keepMounted
            onClose = {props.handleClose}
            aria-labelledby = "table-modal-slide-title"
            aria-describedby = "table-modal-slide-description"
        >
            <DialogTitle
                id = "table-modal-slide-title"
                disableTypography
                className = {classes.modalHeader}
            >
                <IconButton
                    className = {classes.modalCloseButton}
                    key = "Close"
                    aria-label = "close"
                    color = "inherit"
                    onClick = {props.handleClose}
                >
                    <Close className = {classes.modalClose}/>
                </IconButton>
            </DialogTitle>
            <DialogContent
                id = "table-modal-slide-description"
                className = {classes.modalBody}
            >
                <Card>
                    <CardHeader color = "success">
                        <h4 className = {classes.modalTitle}>{props.title}</h4>
                    </CardHeader>
                    <CardBody>
                        <Table
                            tableHeaderColor = "success"
                            tableHead = {props.fields}
                            tableData = {props.tableData}
                        />
                    </CardBody>
                </Card>
            </DialogContent>
        </Dialog>
    );
}

export default withStyles(tableModalStyle)(TableModal);

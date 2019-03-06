import * as React from 'react';
import { withStyles } from "@material-ui/core/styles";
import { connect } from 'react-redux';
import brace from 'brace';
import AceEditor from 'react-ace';
import 'brace/mode/pgsql';
import 'brace/theme/xcode';
import Card from '../Card/Card';
import CardBody from '../Card/CardBody';
import CardHeader from '../Card/CardHeader';
import CustomButton from '../CustomButtons/Button';
import Accordion from "../Accordion/Accordion";
import sqlEditorStyles from '../../assets/jss/frontend/components/sqlEditor.jsx';

import { changeCurrentMode } from '../../store/Actions/ActionCreator';

class SqlEditor extends React.Component {
    constructor(props){
        super(props);
        this.state = {
            editorOptions: {
                mode : 'pgsql',
                theme : 'xcode',
                fontSize : 14,
                showPrintMargin : true,
                showGutter : true,
                highlightActiveLine : true,
                enableBasicAutocompletion : false,
                enableLiveAutocompletion : true,
                enableSnippets : false,
                showLineNumbers : true,
                tabSize : 2,
            },
        };
    }


    render() {
        const { editorOptions } = this.state;
        const { changeCurrentMode ,classes, currentSQL } = this.props;

        const editor = (<AceEditor
            mode={editorOptions.mode}
            width = {'100%'}
            theme={editorOptions.theme}
            name={" SQL Editor"}
            onLoad={this.getCurrentSQL}
            fontSize={editorOptions.fontSize}
            showPrintMargin={editorOptions.showPrintMargin}
            showGutter={editorOptions.showGutter}
            highlightActiveLine={editorOptions.highlightActiveLine}
            value={currentSQL}
            setOptions={{
                enableBasicAutocompletion: editorOptions.enableBasicAutocompletion,
                enableLiveAutocompletion: editorOptions.enableLiveAutocompletion,
                enableSnippets: editorOptions.enableSnippets,
                showLineNumbers: editorOptions.showLineNumbers,
                tabSize: editorOptions.tabSize,
            }}
        />);
        return(
            <Card className={classes.cardBody}>
                <CardHeader><CustomButton onClick={changeCurrentMode}>EDIT</CustomButton></CardHeader>
                <CardBody >
                    <Accordion
                        active={0}
                        collapses={
                            [{
                                title: 'SQL Editor',
                                content: editor
                            }]
                        }
                    />
                </CardBody>
            </Card>

        );
    }

}

const mapStateToProps = state => {
    return {
        currentSQL: state.dataset.sql,
    }
}

const mapDispatchToProps = dispatch => {
    return {
        changeCurrentMode : () => dispatch(changeCurrentMode()),
    }
}


export default connect(mapStateToProps, mapDispatchToProps)(withStyles(sqlEditorStyles)(SqlEditor));
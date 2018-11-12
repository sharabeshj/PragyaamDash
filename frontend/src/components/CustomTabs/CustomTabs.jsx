import React from 'react';
import classNames from 'classnames';
import PropTypes from 'prop-types';

import { withStyles } from '@material-ui/core/styles';
import Tabs from '@material-ui/core/Tabs';
import Tab from '@material-ui/core/Tab';

import Card from '../Card/Card';
import CardBody from '../Card/CardBody';
import CardHeader from '../Card/CardHeader';

import customTabsStyle from '../../assets/jss/frontend/components/customTabsStyle';

class CustomTabs extends React.Component {
    constructor(props){
        super(props);
        this.state = {
            value: 0
        };
    
    }

    handleChange = (event,value) => {
        console.log({"val" : value});
        this.setState({ value : value });
    };

    render() {
        const {
            classes,
            headerColor,
            plainTabs,
            tabs,
            title,
            rtlActive
        } = this.props;
        const cardTitle = classNames({
            [classes.cardTitle]: true,
            [classes.cardTitleRTL]: rtlActive
        });
        return (
            <Card plain={plainTabs}>
                <CardHeader color={headerColor} plain={plainTabs}>
                    {title !== undefined ? (
                        <div className={cardTitle}>
                            {title}
                        </div>
                    ) : null}
                    <Tabs
                        value={this.state.value}
                        onChange={this.handleChange}
                        classes={{
                            root: classes.tabsRoot,
                            indicator: classes.displayNone
                        }}
                        scrollButtons="auto"
                    >
                        {tabs.map((prop, key) => {
                            let icon = {};
                            if (prop.tabIcon) {
                                icon = {
                                    icon: <prop.tabIcon />
                                };
                            }
                            return (
                                <Tab
                                    classes={{
                                        root: classes.tabRootButton,
                                        labelContainer: classes.tabLabelContainer,
                                        label: classes.tabLabel,
                                        selected: classes.tabSelected,
                                        wrapper: classes.tabWrapper
                                    }}
                                    key={key}
                                    label={prop.tabName}
                                    {...icon}
                                />
                            );
                        })}
                    </Tabs>
                </CardHeader>
                <CardBody>
                    {tabs.map((prop, key) => {
                        if (key === this.state.value) {
                            return <div key={key}>{prop.tabContent}</div>
                        }
                        return null;
                    })}
                </CardBody>
            </Card>
        );
    }
}

CustomTabs.propTypes = {
    classes: PropTypes.object.isRequired,
    headerColor: PropTypes.oneOf([
        "warning",
        "success",
        "danger",
        "info",
        "primary"
    ]),
    title: PropTypes.string,
    tabs: PropTypes.arrayOf(
        PropTypes.shape({
            tabName: PropTypes.string.isRequired,
            tabIcon: PropTypes.func,
            tabContent: PropTypes.node.isRequired
        })
    ),
    rtlActive: PropTypes.bool,
    plainTabs: PropTypes.bool
};

export default withStyles(customTabsStyle)(CustomTabs);
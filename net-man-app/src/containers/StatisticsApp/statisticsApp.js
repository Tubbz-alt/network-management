import React, { Component } from 'react';
import { Container, Row, Col, Table, Spinner } from 'reactstrap';
import { withRouter, Redirect } from 'react-router-dom';

//import styles from './statisticsApp.module.css';
import { openDaylightApi } from '../../services/openDaylightApi';

import TopologyGraph from '../TopologyGraph/topologyGraph';
import produce from 'immer';

import { getWidth, getHeight } from '../../utilities/utilities';
import HostInfo from '../../components/StatisticsApp/HostInfo/hostInfo';
import { getGraphLinks, getGraphNodes } from '../../utilities/ODL_utilities';


class StatisticsApp extends Component {

    state = {
        selectedNodeId: this.props.location.data ? Object.keys(this.props.location.data.nodesInfo)[0] : null,
        selectedLinkId: null
    }

    nodeClickedHandler = (nodeId) => {
        
        this.setState(
            produce(draft => {
                draft.selectedNodeId = nodeId;
                draft.selectedLinkId = null;
            })
        );
    }

    linkClickedHandler = (linkId) => {
        // alert(`link clicked ${linkId}`);

        this.setState(
            produce(draft => {
                draft.selectedNodeId = null;
                draft.selectedLinkId = linkId;
            })
        );
    }


    getSelectedType = () => {
        if (this.state.selectedNodeId || this.state.selectedLinkId)
        {
            if (this.state.selectedNodeId)
            { //node clicked: (host or switch)
                return this.props.location.data.nodesInfo[this.state.selectedNodeId].type;
            }
            else
            { // link clicked
                return "link";
            }
        }
        else
        {
            return null;
        }
    }

    renderSideInfo = () => {
        const type = this.getSelectedType();
        // alert(`type: ${type}`)
        if (!type)
        {
            return null;
        }
        else
        {
            if (type === "host")
            {
                return (
                    <HostInfo nodeInfo={this.props.location.data.nodesInfo[this.state.selectedNodeId]}/>    
                );
            }
            else if (type === "switch")
            {
                return "switch";
            }
            else if (type === "link")
            {
                return "link"
            }
            else 
            {
                alert("den paizeis me poiothta"); //REMOVE IT !!!!!!!!!!
                return "den paizeis me poiothta";
            }
        }
    }


    renderSwitchInfo = () => {
        const type = this.getSelectedType();
        if ((!type) || (type !== "switch"))
        {
            return null;
        }
        else
        {
            return (
                <div className="d-flex d-flex-row" style={{borderBottom: "2px solid gray", backgroundColor: "GhostWhite"}}>
                    SWITCH INFO
                </div>
            );
        }
    }


    

    render () {

        console.log("inside statistics app rendering");

        // alert("rendering app")
        console.log(this.props.location.data);
        console.log(this.state)
        const graphWidth = getWidth() * 0.6;
        const graphHeight = getHeight() * 0.7;

        return (
            <>
                {!this.props.location.data ?
                    <Redirect to="/"/>
                :

                    <div style={{borderTop: "2px solid gray", borderLeft: "2px solid gray", borderRight: "2px solid gray"}}>

                        <div className="d-flex d-flex-row justify-content-center" style={{backgroundColor: "GhostWhite"}}>
                            <div className="font-weight-bold customHeader1">
                                Topology Overview
                            </div>
                        </div>

                        <div className="d-flex d-flex-row" style={{borderTop: "2px solid gray", borderBottom: "2px solid gray"}}>
                            <div style={{borderRight: "2px solid gray"}}>
                                <TopologyGraph
                                    nodeClickedHandler={this.nodeClickedHandler}
                                    linkClickedHandler={this.linkClickedHandler}
                                    graphClickedHandler={this.graphClickedHandler}
                                    nodes={getGraphNodes(this.props.location.data.nodesInfo, [this.state.selectedNodeId])}
                                    links={getGraphLinks(this.props.location.data.linksInfo, [this.state.selectedLinkId])}
                                    graphWidth={graphWidth}
                                    graphHeight={graphHeight}
                                />
                            </div>

                            <div className="w-100 p-2" style={{backgroundColor: "GhostWhite"}}>
                                {this.renderSideInfo()}
                            </div>
                        </div>

                        {this.renderSwitchInfo()}
                    </div>
                }
            </>
        )

    }

}


export default withRouter(StatisticsApp);
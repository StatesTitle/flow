import React, { Component } from 'react';

const AffectRow = ({affect, actionList, onSelect}) => {
    let affectedAction = actionList.find(action => `${action.id}-${action.groupId}` === affect.action);
    if (!affectedAction)
        return (<tr>oops</tr>);
    return (
        <tr>
            <td style={{width:'30%'}}><strong>{affect.type}</strong></td>
            <td><a href="#" onClick={() => onSelect(affect.action)} >{affectedAction.name}</a></td>
        </tr>
    );
};

class App extends Component {

    constructor() {
        super();
        this.state = {
            showHidden: false,
            showDynamic: false,
            selectedActionId: '96-16',
            actionList: [],
            filter: ''
        };
        this.actions = {};
    }

    componentDidUpdate() {
        if (this.actions[this.state.selectedActionId]) {
            function scrollIntoView(el) {
                let rect = el.getBoundingClientRect();
                let elemTop = rect.top;
                let elemBottom = rect.bottom;

                // Only completely visible elements return true:
                let isVisible = (elemTop >= 0) && (elemBottom <= window.innerHeight);
                // Partially visible elements return true:
                //isVisible = elemTop < window.innerHeight && elemBottom >= 0;
                if (!isVisible) {
                    if (elemBottom > window.innerHeight)
                        el.scrollIntoView(false);
                    else
                        el.scrollIntoView(true);
                }
            }
            scrollIntoView(this.actions[this.state.selectedActionId]);
        }
    }

    render() {
        const {actionList, selectedActionId} = this.state;
        let selectedAction = actionList.find(action => `${action.id}-${action.groupId}` === selectedActionId);
        return (
            <div className="App">
                    <header className="App-header">
                        <nav className="navbar navbar-expand-lg navbar-light bg-light">
                            <ol className="breadcrumb bg-transparent">
                                <li className="breadcrumb-item"><a href="#">Refinance</a></li>
                                <li className="breadcrumb-item active">Action List</li>
                            </ol>
                        </nav>
                    </header>
                <div className="container-fluid">
                    <div className="row">
                        <div className="col-3">
                            <div className="">
                                <div className="input-group mt-3">
                                    <input type="text" className="form-control" placeholder="Filter" value={this.state.filter} onChange={(e) => this.setState({filter: e.target.value})}/>
                                </div>
                                <div className="m-2">
                                    <div className="form-check form-check-inline">
                                        <input className="form-check-input" type="checkbox" id="hiddenCheckbox"
                                               value="option1" onChange={() => this.setState({showHidden: !this.state.showHidden})}
                                               checked={this.state.showHidden} />
                                            <label className="form-check-label" htmlFor="hiddenCheckbox">hidden</label>
                                    </div>
                                    <div className="form-check form-check-inline">
                                        <input className="form-check-input" type="checkbox" id="dynamicCheckbox"
                                               value="option2" onChange={() => this.setState({showDynamic: !this.state.showDynamic})}
                                               checked={this.state.showDynamic} />
                                            <label className="form-check-label" htmlFor="dynamicCheckbox">dynamic</label>
                                    </div>
                                </div>
                            </div>
                            <div className="list-group list-group-flush border rounded" style={{height: '80vh', overflow: 'auto'}}>
                                <div className="list-group list-group-flush">
                                    {
                                        actionList
                                            .filter(action => this.state.showDynamic || !action.dynamic)
                                            .filter(action => this.state.showHidden || !action.hidden)
                                            .filter(action => action.name.toLowerCase().indexOf(this.state.filter.toLowerCase()) >= 0)
                                            .map(action => {
                                                let key = `${action.id}-${action.groupId}`;
                                                return (
                                                    <a key={key} href="#" ref={el => this.actions[key] = el}
                                                       className={`${this.state.selectedActionId === key ? 'active' : ''} list-group-item list-group-item-action flex-column align-items-start`}
                                                       onClick={() => this.setState({selectedActionId: key })} >
                                                        <div className="row">
                                                            <h6 className="mb-1 col">{action.name}</h6>
                                                            <div className="col-md-auto">
                                                                {[...action.start_affects, ...action.complete_affects].length > 0 &&
                                                                <i className="ml-1 far fa-arrow-alt-circle-right"></i>}
                                                                {[...action.start_emails, ...action.complete_emails].length > 0 &&
                                                                <i className="ml-1 far fa-envelope"></i>}
                                                            </div>
                                                        </div>
                                                    </a>
                                                );
                                            })
                                    }
                                </div>
                            </div>
                        </div>
                        {
                            selectedAction &&
                            (<div className="col">
                                <h2 className="py-2">{selectedAction.name}</h2>
                                <p>{selectedAction.description}</p>
                                <div className="bg-light p-3 mb-2 rounded">
                                    <h3 className="">Start</h3>
                                    <div className="row">
                                        <div className="col">
                                            <h5 className="card-title">Affects</h5>
                                            <table className="table table-borderless table-sm">
                                                <tbody>
                                                {
                                                    selectedAction.start_affects.map(affect => (
                                                        <AffectRow actionList={actionList} affect={affect} onSelect={actionId => this.setState({selectedActionId: actionId })}/>
                                                    ))
                                                }
                                                </tbody>
                                            </table>
                                        </div>
                                        <div className="col">
                                            <h5 className="card-title">Email Templates</h5>
                                            <table className="table table-borderless table-sm">
                                                <tbody>
                                                {
                                                    selectedAction.start_emails.map(email => (
                                                        <tr>
                                                            <td>{email.name}</td>
                                                        </tr>
                                                    ))
                                                }
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                                <div className="bg-light p-3 mb-2 rounded">
                                    <h3 className="bg-light rounded">Complete</h3>
                                    <div className="row">
                                        <div className="col">
                                            <h5 className="card-title">Affects</h5>
                                            <table className="table table-borderless table-sm">
                                                <tbody>
                                                {
                                                    selectedAction.complete_affects.map(affect => (
                                                        <AffectRow actionList={actionList} affect={affect} onSelect={actionId => this.setState({selectedActionId: actionId })}/>
                                                    ))
                                                }
                                                </tbody>
                                            </table>
                                        </div>
                                        <div className="col">
                                            <h5 className="card-title">Email Templates</h5>
                                            <table className="table table-borderless table-sm">
                                                <tbody>
                                                {
                                                    selectedAction.complete_emails.map(email => (
                                                        <tr >
                                                            <td>{email.name}</td>
                                                        </tr>
                                                    ))
                                                }
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>)
                        }
                    </div>
                </div>
            </div>
        );
    }
}

export default App;

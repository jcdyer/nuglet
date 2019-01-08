import React, { Component } from 'react';
import logo from './logo.svg';
import './App.css';

class Image {
  constructor(public url: URL, public caption: String, public votes: Number) {}
}

interface ImageTileProps {
  image: Image,
  selected: boolean,
  onClick: (img: Image) => void,
}

function ImageTile(props: ImageTileProps) {
  return (
    <li className="image-tile" onClick={() => props.onClick(props.image)}>
      <img
        className={props.selected ? "selected" : ""}
        src={props.image.url.href}
      />
      <p>{props.selected ? "selected" : "not selected"}</p>
    </li>
  );
}

interface ImageListState {
  selected: Array<Image>,
}

class ImageList extends Component<{}, ImageListState> {
  constructor(props: {}) {
    super(props);
    this.state = {
      selected: new Array(),
    };
  }

  render() {
    const images = [
      new Image(
        new URL('https://farm5.staticflickr.com/4842/31714049267_3574dd284e_z_d.jpg'),
        "Eat, play, read, sleep. Our lives in a nutshell",
        0,
      ),
      new Image(
        new URL('https://farm5.staticflickr.com/4869/45858024464_74e86a1904_z_d.jpg'),
        "Ready to go",
        1,
      )
    ];
    return (
      <ul className="image-list">
      {images.map((img, idx) =>
        <ImageTile key={img.url.href} image={img} selected={this.state.selected.some((x) => x.url.href === img.url.href)} onClick={() => this.handleClick(img)}/>
      )}
      </ul>
    )
  }

  handleClick(image: Image) {
    console.log("handling click of ", image);
    const selected = this.state.selected.slice();
    console.log("PRESELECTED", selected)
    if (selected.some((el) => el.url.href === image.url.href)) {
      console.log("included");
      this.setState({selected: selected.filter((x) => x.url.href != image.url.href)});
    } else {
      console.log("not included");
      this.setState({selected: selected.concat(image)});
    }
    console.log(this.state.selected)
  }
}

class App extends Component {
  render() {
    return (
      <div className="App">
        <header className="App-header">
          <img src={logo} className="App-logo" alt="logo" />
          <p>
            Edit <code>src/App.tsx</code> and save to reload.
          </p>
          <a
            className="App-link"
            href="https://reactjs.org"
            target="_blank"
            rel="noopener noreferrer"
          >
            Learn React
          </a>
        </header>
        <ImageList/>
      </div>
    );
  }
}

export default App;

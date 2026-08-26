import { Link } from "react-router-dom";

export function Home() {
  return (
    <main className="page home">
      <h1>What's in your fridge?</h1>
      <p>Fridge input and meal suggestions are coming in a later milestone.</p>
      <Link to="/settings">Settings</Link>
    </main>
  );
}

import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppGate } from "./components/AppGate";
import { Home } from "./pages/Home";
import { Onboarding } from "./pages/Onboarding";
import { Settings } from "./pages/Settings";
import { SuggestionsResult } from "./pages/SuggestionsResult";
import { Unlock } from "./pages/Unlock";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/unlock" element={<Unlock />} />
        <Route
          path="/"
          element={
            <AppGate>
              <Home />
            </AppGate>
          }
        />
        <Route
          path="/results"
          element={
            <AppGate>
              <SuggestionsResult />
            </AppGate>
          }
        />
        <Route
          path="/settings"
          element={
            <AppGate>
              <Settings />
            </AppGate>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

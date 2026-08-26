import { BrowserRouter, Route, Routes } from "react-router-dom";
import { RequireOnboarding } from "./components/RequireOnboarding";
import { Home } from "./pages/Home";
import { Onboarding } from "./pages/Onboarding";
import { Settings } from "./pages/Settings";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/onboarding" element={<Onboarding />} />
        <Route
          path="/"
          element={
            <RequireOnboarding>
              <Home />
            </RequireOnboarding>
          }
        />
        <Route
          path="/settings"
          element={
            <RequireOnboarding>
              <Settings />
            </RequireOnboarding>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

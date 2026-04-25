import { createContext } from 'react';

/** The React context object — kept in its own module so both the provider
 *  component and the consumer hook can import it without breaking React Fast
 *  Refresh boundaries. */
export const JobContext = createContext(null);
